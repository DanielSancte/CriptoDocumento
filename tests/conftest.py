"""PDF fixture factories used by the service-level tests."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pikepdf
import pytest


PdfFactory = Callable[..., Path]


def _add_text_page(document: pikepdf.Pdf, label: str) -> pikepdf.Page:
    page = document.add_blank_page(page_size=(300, 300))
    font = document.make_indirect(
        pikepdf.Dictionary(
            Type=pikepdf.Name.Font,
            Subtype=pikepdf.Name.Type1,
            BaseFont=pikepdf.Name.Helvetica,
        )
    )
    page.Resources = pikepdf.Dictionary(Font=pikepdf.Dictionary(F1=font))
    page.Contents = document.make_stream(
        f"BT /F1 14 Tf 30 150 Td ({label}) Tj ET\n".encode("ascii")
    )
    return page


def _save_plain_pdf(path: Path, labels: Sequence[str]) -> Path:
    with pikepdf.Pdf.new() as document:
        for label in labels:
            _add_text_page(document, label)
        document.save(path)
    return path


def _appearance_stream(
    document: pikepdf.Pdf, marker: str, color: tuple[float, float, float]
) -> pikepdf.Stream:
    red, green, blue = color
    appearance = document.make_stream(
        (
            f"q {red} {green} {blue} rg 0 0 80 20 re f "
            f"% {marker}\nQ\n"
        ).encode("ascii")
    )
    appearance.Type = pikepdf.Name.XObject
    appearance.Subtype = pikepdf.Name.Form
    appearance.BBox = pikepdf.Array([0, 0, 80, 20])
    appearance.Resources = pikepdf.Dictionary()
    return appearance


@pytest.fixture
def minimal_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(name: str = "minimal.pdf", label: str = "MINIMAL") -> Path:
        return _save_plain_pdf(tmp_path / name, (label,))

    return create


@pytest.fixture
def multipage_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(
        name: str = "multipage.pdf", labels: Sequence[str] = ("FIRST", "SECOND")
    ) -> Path:
        return _save_plain_pdf(tmp_path / name, labels)

    return create


@pytest.fixture
def encrypted_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(name: str = "encrypted.pdf") -> Path:
        path = tmp_path / name
        with pikepdf.Pdf.new() as document:
            _add_text_page(document, "ENCRYPTED")
            document.save(
                path,
                encryption=pikepdf.Encryption(
                    user="source-password",
                    owner="source-owner-password",
                    R=6,
                    aes=True,
                ),
            )
        return path

    return create


@pytest.fixture
def damaged_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(name: str = "damaged.pdf") -> Path:
        path = tmp_path / name
        path.write_bytes(b"This is not a PDF document.\n")
        return path

    return create


@pytest.fixture
def signed_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(name: str = "signed.pdf", *, certification_only: bool = False) -> Path:
        path = tmp_path / name
        with pikepdf.Pdf.new() as document:
            _add_text_page(document, "SIGNED")
            signature = document.make_indirect(
                pikepdf.Dictionary(Type=pikepdf.Name.Sig, Filter=pikepdf.Name.Adobe_PPKLite)
            )
            if certification_only:
                document.Root.Perms = pikepdf.Dictionary(DocMDP=signature)
            else:
                signature_field = document.make_indirect(
                    pikepdf.Dictionary(
                        FT=pikepdf.Name.Sig,
                        T=pikepdf.String("signature-field"),
                        V=signature,
                    )
                )
                document.Root.AcroForm = pikepdf.Dictionary(
                    Fields=pikepdf.Array([signature_field])
                )
            document.save(path)
        return path

    return create


@pytest.fixture
def unflattenable_pdf_factory(tmp_path: Path) -> PdfFactory:
    def create(name: str = "missing-appearance.pdf") -> Path:
        path = tmp_path / name
        with pikepdf.Pdf.new() as document:
            page = _add_text_page(document, "VISIBLE-PAGE")
            annotation = document.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Text,
                    Rect=pikepdf.Array([20, 220, 100, 240]),
                    Contents=pikepdf.String("No appearance stream"),
                )
            )
            annotation.P = page.obj
            page.Annots = pikepdf.Array([annotation])
            document.save(path)
        return path

    return create


@pytest.fixture
def active_pdf_factory(tmp_path: Path) -> PdfFactory:
    """Create one PDF containing every active/inherited structure we remove."""

    def create(name: str = "active.pdf", label: str = "ACTIVE") -> Path:
        path = tmp_path / name
        with pikepdf.Pdf.new() as document:
            page = _add_text_page(document, label)
            javascript_action = document.make_indirect(
                pikepdf.Dictionary(
                    S=pikepdf.Name.JavaScript,
                    JS=pikepdf.String("app.alert('unsafe')"),
                )
            )
            document.Root.OpenAction = javascript_action
            document.Root.AA = pikepdf.Dictionary(WC=javascript_action)
            document.Root.Names = pikepdf.Dictionary(
                JavaScript=pikepdf.Dictionary(
                    Names=pikepdf.Array(
                        [pikepdf.String("startup"), javascript_action]
                    )
                )
            )
            document.Root.Outlines = pikepdf.Dictionary(
                Type=pikepdf.Name.Outlines, Count=0
            )
            document.Root.Metadata = document.make_stream(
                b"""<?xpacket begin=''?>
<x:xmpmeta xmlns:x='adobe:ns:meta/'>
  <rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>
    <rdf:Description rdf:about=''/>
  </rdf:RDF>
</x:xmpmeta>
<?xpacket end='w'?>"""
            )
            document.Root.Metadata.Type = pikepdf.Name.Metadata
            document.Root.Metadata.Subtype = pikepdf.Name.XML
            document.docinfo["/Title"] = "Unsafe inherited title"
            document.attachments["payload.txt"] = b"embedded payload"

            page.AA = pikepdf.Dictionary(O=javascript_action)
            page.Metadata = document.Root.Metadata
            document.Root.Pages.Metadata = document.Root.Metadata

            annotation = document.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Stamp,
                    Rect=pikepdf.Array([20, 220, 100, 240]),
                    F=4,
                    AP=pikepdf.Dictionary(
                        N=_appearance_stream(
                            document, "ANNOTATION_APPEARANCE", (1.0, 0.0, 0.0)
                        )
                    ),
                )
            )
            annotation.P = page.obj
            widget = document.make_indirect(
                pikepdf.Dictionary(
                    Type=pikepdf.Name.Annot,
                    Subtype=pikepdf.Name.Widget,
                    FT=pikepdf.Name.Tx,
                    T=pikepdf.String("visible-form-field"),
                    V=pikepdf.String("visible form value"),
                    Rect=pikepdf.Array([20, 180, 100, 200]),
                    F=4,
                    AP=pikepdf.Dictionary(
                        N=_appearance_stream(
                            document, "FORM_APPEARANCE", (0.0, 0.0, 1.0)
                        )
                    ),
                )
            )
            widget.P = page.obj
            page.Annots = pikepdf.Array([annotation, widget])
            document.Root.AcroForm = pikepdf.Dictionary(
                Fields=pikepdf.Array([widget]), NeedAppearances=False
            )
            document.save(path)
        return path

    return create
