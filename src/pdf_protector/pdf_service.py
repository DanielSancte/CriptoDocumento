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
_GRAPH_KEYS_TO_REMOVE = frozenset(
    {
        "/A",
        "/AA",
        "/AF",
        "/EF",
        "/EmbeddedFiles",
        "/JavaScript",
        "/JS",
        "/Metadata",
        "/OpenAction",
    }
)
_ACTIVE_ACTION_TYPES = frozenset(
    {
        pikepdf.Name.GoTo,
        pikepdf.Name.GoTo3DView,
        pikepdf.Name.GoToR,
        pikepdf.Name.GoToE,
        pikepdf.Name.Hide,
        pikepdf.Name.ImportData,
        pikepdf.Name.JavaScript,
        pikepdf.Name.Launch,
        pikepdf.Name.Movie,
        pikepdf.Name.Named,
        pikepdf.Name.ResetForm,
        pikepdf.Name.RichMediaExecute,
        pikepdf.Name.Rendition,
        pikepdf.Name.SetOCGState,
        pikepdf.Name.Sound,
        pikepdf.Name.SubmitForm,
        pikepdf.Name.Thread,
        pikepdf.Name.Trans,
        pikepdf.Name.URI,
    }
)
_FORBIDDEN_OBJECT_TYPES = frozenset(
    {
        pikepdf.Name.Action,
        pikepdf.Name.EmbeddedFile,
        pikepdf.Name.Filespec,
        pikepdf.Name.Metadata,
    }
)
_STRUCTURAL_ERRORS = (
    AttributeError,
    IndexError,
    KeyError,
    TypeError,
    ValueError,
    RuntimeError,
)


@contextmanager
def _open_source(path: Path) -> Iterator[pikepdf.Pdf]:
    try:
        with pikepdf.open(path, password="") as document:
            if document.is_encrypted:
                raise SourcePdfError(
                    f"El PDF de origen '{path.name}' está protegido con contraseña.",
                    path=path,
                )
            yield document
    except SourcePdfError:
        raise
    except (OSError, pikepdf.PasswordError, pikepdf.PdfError, *_STRUCTURAL_ERRORS) as error:
        raise SourcePdfError(
            f"No se pudo abrir o procesar el PDF de origen '{path.name}'.",
            path=path,
        ) from error


def _field_tree_has_signature(
    fields: object,
    path: Path,
    is_cancelled: Callable[[], bool],
) -> bool:
    if not isinstance(fields, pikepdf.Array):
        raise SourcePdfError(
            f"La estructura de firmas de '{path.name}' no es válida.", path=path
        )
    pending = list(fields)
    visited: set[tuple[int, int] | int] = set()

    while pending:
        _raise_if_cancelled(is_cancelled)
        field = pending.pop()
        if not isinstance(field, pikepdf.Dictionary):
            raise SourcePdfError(
                f"La estructura de firmas de '{path.name}' no es válida.", path=path
            )
        object_number = field.objgen
        identity: tuple[int, int] | int = (
            object_number if object_number != (0, 0) else id(field)
        )
        if identity in visited:
            continue
        visited.add(identity)

        if field.get("/FT") == pikepdf.Name.Sig:
            return True
        children = field.get("/Kids")
        if children is not None:
            if not isinstance(children, pikepdf.Array):
                raise SourcePdfError(
                    f"La estructura de firmas de '{path.name}' no es válida.",
                    path=path,
                )
            pending.extend(children)

    return False


def _has_signatures(
    document: pikepdf.Pdf,
    path: Path,
    is_cancelled: Callable[[], bool],
) -> bool:
    permissions = document.Root.get("/Perms")
    if permissions is not None:
        if not isinstance(permissions, pikepdf.Dictionary):
            raise SourcePdfError(
                f"La estructura de firmas de '{path.name}' no es válida.", path=path
            )
        if permissions.get("/DocMDP") is not None:
            return True

    acroform = document.Root.get("/AcroForm")
    if acroform is None:
        return False
    if not isinstance(acroform, pikepdf.Dictionary):
        raise SourcePdfError(
            f"La estructura de formulario de '{path.name}' no es válida.", path=path
        )
    return _field_tree_has_signature(
        acroform.get("/Fields", pikepdf.Array()), path, is_cancelled
    )


def inspect_source(
    path: Path,
    is_cancelled: Callable[[], bool] = lambda: False,
) -> SourceInspection:
    """Inspect an unencrypted source PDF without retaining an open file handle."""
    _raise_if_cancelled(is_cancelled)
    with _open_source(path) as document:
        return SourceInspection(
            path=path,
            pages=len(document.pages),
            has_signatures=_has_signatures(document, path, is_cancelled),
        )


def _remove_keys(dictionary: pikepdf.Dictionary, keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in dictionary:
            del dictionary[key]


def _remove_inherited_page_metadata(
    node: object,
    path: Path | None,
    is_cancelled: Callable[[], bool],
) -> None:
    _raise_if_cancelled(is_cancelled)
    if not isinstance(node, pikepdf.Dictionary):
        if path is None:
            raise pikepdf.PdfError("invalid page tree")
        raise SourcePdfError(
            f"La estructura de páginas de '{path.name}' no es válida.", path=path
        )
    _remove_keys(node, _PAGE_KEYS_TO_REMOVE)
    children = node.get("/Kids", pikepdf.Array())
    if not isinstance(children, pikepdf.Array):
        if path is None:
            raise pikepdf.PdfError("invalid page tree children")
        raise SourcePdfError(
            f"La estructura de páginas de '{path.name}' no es válida.", path=path
        )
    for child in children:
        _raise_if_cancelled(is_cancelled)
        if not isinstance(child, pikepdf.Dictionary):
            if path is None:
                raise pikepdf.PdfError("invalid page tree child")
            raise SourcePdfError(
                f"La estructura de páginas de '{path.name}' no es válida.", path=path
            )
        if child.get("/Type") == pikepdf.Name.Pages:
            _remove_inherited_page_metadata(child, path, is_cancelled)


def _normal_appearance(annotation: object, path: Path) -> object | None:
    if not isinstance(annotation, pikepdf.Dictionary):
        raise SourcePdfError(
            f"La estructura de anotaciones de '{path.name}' no es válida.", path=path
        )
    appearances = annotation.get("/AP")
    if appearances is None:
        return None
    if not isinstance(appearances, pikepdf.Dictionary):
        raise SourcePdfError(
            f"La apariencia de una anotación de '{path.name}' no es válida.",
            path=path,
        )
    return appearances.get("/N")


def _flatten_visible_annotations(
    document: pikepdf.Pdf,
    path: Path,
    is_cancelled: Callable[[], bool],
) -> None:
    _raise_if_cancelled(is_cancelled)
    document.generate_appearance_streams()
    for page in document.pages:
        _raise_if_cancelled(is_cancelled)
        annotations = page.obj.get("/Annots", pikepdf.Array())
        if not isinstance(annotations, pikepdf.Array):
            raise SourcePdfError(
                f"La estructura de anotaciones de '{path.name}' no es válida.",
                path=path,
            )
        for annotation in annotations:
            _raise_if_cancelled(is_cancelled)
            if _normal_appearance(annotation, path) is None:
                raise SourcePdfError(
                    "No se puede aplanar de forma segura la apariencia de "
                    f"'{path.name}'.",
                    path=path,
                )

    _raise_if_cancelled(is_cancelled)
    document.flatten_annotations(mode="all")
    for page in document.pages:
        _raise_if_cancelled(is_cancelled)
        annotations = page.obj.get("/Annots")
        if annotations is not None and len(annotations) > 0:
            raise SourcePdfError(
                f"No se pudieron aplanar todas las anotaciones de '{path.name}'.",
                path=path,
            )
        if "/Annots" in page.obj:
            del page.obj["/Annots"]


def _object_identity(item: object) -> tuple[int, int] | int:
    objgen = getattr(item, "objgen", (0, 0))
    return objgen if objgen != (0, 0) else id(item)


def _is_graph_container(item: object) -> bool:
    return isinstance(item, (pikepdf.Array, pikepdf.Dictionary, pikepdf.Stream))


def _is_forbidden_graph_object(item: object) -> bool:
    if not isinstance(item, (pikepdf.Dictionary, pikepdf.Stream)):
        return False
    return (
        item.get("/Type") in _FORBIDDEN_OBJECT_TYPES
        or item.get("/S") in _ACTIVE_ACTION_TYPES
    )


def _sanitize_reachable_graph(
    root: object,
    *,
    is_cancelled: Callable[[], bool],
) -> None:
    """Remove unsafe objects from every container reachable from ``root``."""
    pending = [root]
    visited: set[tuple[int, int] | int] = set()
    retained_direct_objects: list[object] = []

    while pending:
        _raise_if_cancelled(is_cancelled)
        item = pending.pop()
        if not _is_graph_container(item):
            continue
        identity = _object_identity(item)
        if identity in visited:
            continue
        visited.add(identity)
        if getattr(item, "objgen", (0, 0)) == (0, 0):
            retained_direct_objects.append(item)

        if isinstance(item, pikepdf.Array):
            for index in range(len(item) - 1, -1, -1):
                _raise_if_cancelled(is_cancelled)
                child = item[index]
                if _is_forbidden_graph_object(child):
                    del item[index]
                elif _is_graph_container(child):
                    pending.append(child)
            continue

        for key in list(item.keys()):
            _raise_if_cancelled(is_cancelled)
            if str(key) in _GRAPH_KEYS_TO_REMOVE:
                del item[key]
                continue
            child = item.get(key)
            if _is_forbidden_graph_object(child):
                del item[key]
            elif _is_graph_container(child):
                pending.append(child)


def _sanitize_source(
    document: pikepdf.Pdf,
    path: Path,
    is_cancelled: Callable[[], bool],
) -> None:
    acroform = document.Root.get("/AcroForm")
    if acroform is not None and not isinstance(acroform, pikepdf.Dictionary):
        raise SourcePdfError(
            f"La estructura de formulario de '{path.name}' no es válida.", path=path
        )
    if acroform is not None and "/XFA" in acroform:
        raise SourcePdfError(
            "No se puede preservar de forma segura el formulario XFA de "
            f"'{path.name}'.",
            path=path,
        )
    _flatten_visible_annotations(document, path, is_cancelled)
    _remove_inherited_page_metadata(document.Root.Pages, path, is_cancelled)
    for page in document.pages:
        _raise_if_cancelled(is_cancelled)
        _remove_keys(page.obj, _PAGE_KEYS_TO_REMOVE)
    _sanitize_reachable_graph(document.Root, is_cancelled=is_cancelled)


def _sanitize_output(
    document: pikepdf.Pdf,
    is_cancelled: Callable[[], bool],
) -> None:
    _remove_keys(document.Root, _ROOT_KEYS_TO_REMOVE)
    names = document.Root.get("/Names")
    if names is not None:
        _remove_keys(names, ("/EmbeddedFiles", "/JavaScript"))
        if len(names) == 0:
            del document.Root["/Names"]
    document.attachments.clear()
    for key in list(document.docinfo.keys()):
        del document.docinfo[key]
    _remove_inherited_page_metadata(document.Root.Pages, None, is_cancelled)
    for page in document.pages:
        _raise_if_cancelled(is_cancelled)
        _remove_keys(page.obj, _PAGE_KEYS_TO_REMOVE)
    _sanitize_reachable_graph(document.Root, is_cancelled=is_cancelled)


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
        total_pages += inspect_source(path, is_cancelled=is_cancelled).pages

    processed_pages = 0
    with pikepdf.Pdf.new() as output:
        for path in request.sources:
            _raise_if_cancelled(is_cancelled)
            with _open_source(path) as source:
                _sanitize_source(source, path, is_cancelled)
                for page in source.pages:
                    _raise_if_cancelled(is_cancelled)
                    output.pages.append(page)
                    processed_pages += 1
                    if on_progress is not None:
                        on_progress(processed_pages, total_pages)
                    _raise_if_cancelled(is_cancelled)

        _raise_if_cancelled(is_cancelled)
        _sanitize_output(output, is_cancelled)
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
