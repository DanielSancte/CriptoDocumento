"""In-memory PDF inspection, sanitization, merging, and encryption."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import BinaryIO

import pikepdf

from pdf_protector.domain import (
    CancelledError,
    PdfPermissions,
    ProtectionRequest,
    SourceInspection,
    SourcePdfError,
)
from pdf_protector.passwords import generate_owner_password


_ROOT_KEYS_TO_REMOVE = (
    "/AA",
    "/AcroForm",
    "/AF",
    "/Collection",
    "/Metadata",
    "/OpenAction",
    "/Outlines",
    "/Perms",
    "/PieceInfo",
)
_PAGE_KEYS_TO_REMOVE = ("/AA", "/AF", "/Metadata", "/PieceInfo")


@contextmanager
def _open_source(path: Path) -> Iterator[pikepdf.Pdf]:
    try:
        with pikepdf.open(path, password="") as document:
            yield document
    except (OSError, pikepdf.PasswordError, pikepdf.PdfError) as error:
        raise SourcePdfError(
            f"No se pudo abrir el PDF de origen '{path.name}'."
        ) from error


def _field_tree_has_signature(fields: pikepdf.Array) -> bool:
    pending = list(fields)
    visited: set[tuple[int, int] | int] = set()

    while pending:
        field = pending.pop()
        object_number = field.objgen
        identity: tuple[int, int] | int = object_number if object_number != (0, 0) else id(field)
        if identity in visited:
            continue
        visited.add(identity)

        if field.get("/FT") == pikepdf.Name.Sig:
            return True
        pending.extend(field.get("/Kids", ()))

    return False


def _has_signatures(document: pikepdf.Pdf) -> bool:
    permissions = document.Root.get("/Perms")
    if permissions is not None and permissions.get("/DocMDP") is not None:
        return True

    acroform = document.Root.get("/AcroForm")
    if acroform is None:
        return False
    return _field_tree_has_signature(acroform.get("/Fields", pikepdf.Array()))


def inspect_source(path: Path) -> SourceInspection:
    """Inspect an unencrypted source PDF without retaining an open file handle."""
    with _open_source(path) as document:
        return SourceInspection(
            path=path,
            pages=len(document.pages),
            has_signatures=_has_signatures(document),
        )


def _remove_keys(dictionary: pikepdf.Dictionary, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in dictionary:
            del dictionary[key]


def _remove_inherited_page_metadata(node: pikepdf.Dictionary) -> None:
    _remove_keys(node, _PAGE_KEYS_TO_REMOVE)
    for child in node.get("/Kids", ()):
        if child.get("/Type") == pikepdf.Name.Pages:
            _remove_inherited_page_metadata(child)


def _normal_appearance(annotation: pikepdf.Dictionary) -> object | None:
    appearances = annotation.get("/AP")
    if appearances is None:
        return None
    return appearances.get("/N")


def _flatten_visible_annotations(document: pikepdf.Pdf, path: Path) -> None:
    document.generate_appearance_streams()
    for page in document.pages:
        for annotation in page.obj.get("/Annots", ()):
            if _normal_appearance(annotation) is None:
                raise SourcePdfError(
                    "No se puede aplanar de forma segura la apariencia de "
                    f"'{path.name}'."
                )

    document.flatten_annotations(mode="all")
    for page in document.pages:
        annotations = page.obj.get("/Annots")
        if annotations is not None and len(annotations) > 0:
            raise SourcePdfError(
                f"No se pudieron aplanar todas las anotaciones de '{path.name}'."
            )
        if "/Annots" in page.obj:
            del page.obj["/Annots"]


def _sanitize_source(document: pikepdf.Pdf, path: Path) -> None:
    acroform = document.Root.get("/AcroForm")
    if acroform is not None and "/XFA" in acroform:
        raise SourcePdfError(
            "No se puede preservar de forma segura el formulario XFA de "
            f"'{path.name}'."
        )
    _flatten_visible_annotations(document, path)
    _remove_inherited_page_metadata(document.Root.Pages)
    for page in document.pages:
        _remove_keys(page.obj, _PAGE_KEYS_TO_REMOVE)


def _sanitize_output(document: pikepdf.Pdf) -> None:
    _remove_keys(document.Root, _ROOT_KEYS_TO_REMOVE)
    names = document.Root.get("/Names")
    if names is not None:
        _remove_keys(names, ("/EmbeddedFiles", "/JavaScript"))
        if len(names) == 0:
            del document.Root["/Names"]
    document.attachments.clear()
    for key in list(document.docinfo.keys()):
        del document.docinfo[key]
    _remove_inherited_page_metadata(document.Root.Pages)
    for page in document.pages:
        _remove_keys(page.obj, _PAGE_KEYS_TO_REMOVE)


def _encryption_permissions(permissions: PdfPermissions) -> pikepdf.Permissions:
    return pikepdf.Permissions(
        accessibility=True,
        extract=permissions.copying,
        modify_annotation=permissions.editing,
        modify_assembly=permissions.editing,
        modify_form=permissions.editing,
        modify_other=permissions.editing,
        print_lowres=permissions.printing,
        print_highres=permissions.printing,
    )


def _raise_if_cancelled(is_cancelled: Callable[[], bool]) -> None:
    if is_cancelled():
        raise CancelledError("La protección del PDF fue cancelada.")


def build_encrypted_pdf(
    request: ProtectionRequest,
    sink: BinaryIO,
    is_cancelled: Callable[[], bool] = lambda: False,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Sanitize and merge sources, then write only encrypted bytes to ``sink``."""
    total_pages = 0
    for path in request.sources:
        _raise_if_cancelled(is_cancelled)
        total_pages += inspect_source(path).pages

    processed_pages = 0
    with pikepdf.Pdf.new() as output:
        for path in request.sources:
            _raise_if_cancelled(is_cancelled)
            with _open_source(path) as source:
                _sanitize_source(source, path)
                for page in source.pages:
                    output.pages.append(page)
                    processed_pages += 1
                    if on_progress is not None:
                        on_progress(processed_pages, total_pages)

        _raise_if_cancelled(is_cancelled)
        _sanitize_output(output)
        output.save(
            sink,
            encryption=pikepdf.Encryption(
                R=6,
                aes=True,
                metadata=True,
                user=request.user_password,
                owner=generate_owner_password(),
                allow=_encryption_permissions(request.permissions),
            ),
        )

    return total_pages
