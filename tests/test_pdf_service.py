"""Tests for PDF inspection, sanitization, merging, and encryption."""

from __future__ import annotations

from io import BytesIO
import hashlib
import itertools
import re
from pathlib import Path

import pikepdf
import pytest
from pikepdf.models.encryption import EncryptionMethod

from pdf_protector import pdf_service
from pdf_protector.domain import (
    CancelledError,
    PdfPermissions,
    ProtectionRequest,
    SourcePdfError,
)
from pdf_protector.pdf_service import build_encrypted_pdf, inspect_source


USER_PASSWORD = "opening-password"


def _request(
    sources: tuple[Path, ...],
    destination: Path,
    permissions: PdfPermissions = PdfPermissions(False, False, False),
) -> ProtectionRequest:
    return ProtectionRequest(
        sources=sources,
        destination=destination,
        user_password=USER_PASSWORD,
        permissions=permissions,
    )


def _page_content(page: pikepdf.Page) -> bytes:
    contents = page.obj.get("/Contents")
    if isinstance(contents, pikepdf.Array):
        return b"\n".join(stream.read_bytes() for stream in contents)
    return contents.read_bytes()


def _stream_payloads(document: pikepdf.Pdf) -> list[bytes]:
    return [
        item.read_bytes()
        for item in document.objects
        if isinstance(item, pikepdf.Stream)
    ]


def test_inspect_counts_pages_and_releases_the_source(
    multipage_pdf_factory,
) -> None:
    """Catches a wrong page count or a source handle retained after inspection."""
    source = multipage_pdf_factory(labels=("ONE", "TWO", "THREE"))

    inspection = inspect_source(source)

    assert inspection.path == source
    assert inspection.pages == 3
    assert inspection.has_signatures is False
    source.unlink()
    assert not source.exists()


@pytest.mark.parametrize("certification_only", [False, True], ids=["field", "docmdp"])
def test_inspect_detects_signature_fields_and_certification_signatures(
    signed_pdf_factory, certification_only: bool
) -> None:
    """Catches signed sources being presented as unsigned before processing."""
    source = signed_pdf_factory(
        f"signed-{certification_only}.pdf", certification_only=certification_only
    )

    assert inspect_source(source).has_signatures is True


@pytest.mark.parametrize("source_kind", ["encrypted", "damaged", "missing"])
def test_inspect_reports_known_source_errors_with_the_file_name(
    source_kind: str,
    encrypted_pdf_factory,
    damaged_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches opaque source failures that do not identify the affected file."""
    if source_kind == "encrypted":
        source = encrypted_pdf_factory("locked-input.pdf")
    elif source_kind == "damaged":
        source = damaged_pdf_factory("broken-input.pdf")
    else:
        source = tmp_path / "missing-input.pdf"

    with pytest.raises(SourcePdfError, match=re.escape(source.name)):
        inspect_source(source)


def test_combine_preserves_source_order_total_progress_and_original_bytes(
    minimal_pdf_factory,
    multipage_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches reordering, missing pages, source mutation, or destination writes."""
    first = minimal_pdf_factory("first.pdf", "FIRST-SOURCE")
    second = multipage_pdf_factory(
        "second.pdf", labels=("SECOND-SOURCE-A", "SECOND-SOURCE-B")
    )
    originals = {
        path: hashlib.sha256(path.read_bytes()).digest() for path in (first, second)
    }
    destination = tmp_path / "must-not-be-written-by-core.pdf"
    sink = BytesIO()
    progress: list[tuple[int, int]] = []

    pages = build_encrypted_pdf(
        _request((first, second), destination),
        sink,
        on_progress=lambda current, total: progress.append((current, total)),
    )

    assert pages == 3
    assert progress == [(1, 3), (2, 3), (3, 3)]
    assert not destination.exists()
    assert {
        path: hashlib.sha256(path.read_bytes()).digest() for path in (first, second)
    } == originals
    with pikepdf.open(BytesIO(sink.getvalue()), password=USER_PASSWORD) as combined:
        assert len(combined.pages) == 3
        assert b"FIRST-SOURCE" in _page_content(combined.pages[0])
        assert b"SECOND-SOURCE-A" in _page_content(combined.pages[1])
        assert b"SECOND-SOURCE-B" in _page_content(combined.pages[2])


def test_sanitize_removes_active_content_and_flattens_visible_appearances(
    active_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches active structures surviving or visible annotations disappearing."""
    source = active_pdf_factory()
    with pikepdf.open(source) as unsafe:
        assert "/OpenAction" in unsafe.Root
        assert "/AA" in unsafe.Root
        assert "/JavaScript" in unsafe.Root.Names
        assert "/EmbeddedFiles" in unsafe.Root.Names
        assert "/AcroForm" in unsafe.Root
        assert "/Outlines" in unsafe.Root
        assert "/Metadata" in unsafe.Root.Pages
        assert len(unsafe.pages[0].Annots) == 2

    sink = BytesIO()
    build_encrypted_pdf(_request((source,), tmp_path / "unused.pdf"), sink)

    with pikepdf.open(BytesIO(sink.getvalue()), password=USER_PASSWORD) as sanitized:
        for forbidden in ("/OpenAction", "/AA", "/AcroForm", "/Outlines", "/Metadata"):
            assert forbidden not in sanitized.Root
        if "/Names" in sanitized.Root:
            assert "/JavaScript" not in sanitized.Root.Names
            assert "/EmbeddedFiles" not in sanitized.Root.Names
        assert list(sanitized.attachments.keys()) == []
        assert "/Title" not in sanitized.docinfo

        page = sanitized.pages[0]
        assert "/Annots" not in page.obj
        assert "/AA" not in page.obj
        assert "/Metadata" not in page.obj
        parent = page.obj.get("/Parent")
        while parent is not None:
            assert "/Metadata" not in parent
            parent = parent.get("/Parent")

        payloads = _stream_payloads(sanitized)
        assert any(b"ANNOTATION_APPEARANCE" in payload for payload in payloads)
        assert any(b"FORM_APPEARANCE" in payload for payload in payloads)
        assert b" Do" in _page_content(page)


def test_sanitize_reports_a_technical_limitation_instead_of_dropping_appearance(
    unflattenable_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches silently deleting a visible annotation that cannot be flattened."""
    source = unflattenable_pdf_factory("unsafe-to-flatten.pdf")
    sink = BytesIO()

    with pytest.raises(SourcePdfError, match=r"segura.*unsafe\-to\-flatten\.pdf"):
        build_encrypted_pdf(_request((source,), tmp_path / "unused.pdf"), sink)

    assert sink.getvalue() == b""


def test_sanitize_rejects_xfa_instead_of_discarding_its_visible_presentation(
    xfa_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches XFA presentation being discarded without a proven static rendering."""
    source = xfa_pdf_factory("visible-xfa-input.pdf")
    with pikepdf.open(source) as xfa_source:
        assert "/XFA" in xfa_source.Root.AcroForm
    sink = BytesIO()

    with pytest.raises(SourcePdfError, match=r"XFA.*visible\-xfa\-input\.pdf"):
        build_encrypted_pdf(_request((source,), tmp_path / "unused.pdf"), sink)

    assert sink.getvalue() == b""


def test_cancel_between_sources_raises_without_writing_the_sink(
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches cancellation being ignored after one source has been processed."""
    first = minimal_pdf_factory("first.pdf", "FIRST")
    second = minimal_pdf_factory("second.pdf", "SECOND")
    processed_pages = 0
    sink = BytesIO()

    def record_progress(current: int, _total: int) -> None:
        nonlocal processed_pages
        processed_pages = current

    with pytest.raises(CancelledError):
        build_encrypted_pdf(
            _request((first, second), tmp_path / "unused.pdf"),
            sink,
            is_cancelled=lambda: processed_pages >= 1,
            on_progress=record_progress,
        )

    assert processed_pages == 1
    assert sink.getvalue() == b""


def test_encrypt_requires_the_user_password_and_uses_aes256_revision_6(
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches plaintext output, weak encryption, or an incorrect algorithm revision."""
    source = minimal_pdf_factory()
    sink = BytesIO()

    build_encrypted_pdf(_request((source,), tmp_path / "unused.pdf"), sink)
    encrypted_bytes = sink.getvalue()

    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(BytesIO(encrypted_bytes), password="wrong-password")
    with pikepdf.open(BytesIO(encrypted_bytes), password=USER_PASSWORD) as encrypted:
        assert encrypted.encryption.bits == 256
        assert encrypted.encryption.R == 6
        assert encrypted.trailer.Encrypt.get("/EncryptMetadata", True) is True
        assert encrypted.encryption.file_method is EncryptionMethod.aesv3
        assert encrypted.encryption.stream_method is EncryptionMethod.aesv3
        assert encrypted.encryption.string_method is EncryptionMethod.aesv3


def test_encrypt_generates_a_fresh_owner_password_for_each_output(
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches reusing one administrative password across protected documents."""
    source = minimal_pdf_factory()
    known_owners = iter(("known-owner-one", "known-owner-two"))
    monkeypatch.setattr(
        pdf_service, "generate_owner_password", lambda: next(known_owners)
    )
    first_sink = BytesIO()
    second_sink = BytesIO()

    build_encrypted_pdf(_request((source,), tmp_path / "first.pdf"), first_sink)
    build_encrypted_pdf(_request((source,), tmp_path / "second.pdf"), second_sink)

    with pikepdf.open(
        BytesIO(first_sink.getvalue()), password="known-owner-one"
    ) as first:
        assert first.owner_password_matched is True
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(BytesIO(first_sink.getvalue()), password="known-owner-two")
    with pikepdf.open(
        BytesIO(second_sink.getvalue()), password="known-owner-two"
    ) as second:
        assert second.owner_password_matched is True
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(BytesIO(second_sink.getvalue()), password="known-owner-one")


@pytest.mark.parametrize(
    ("printing", "copying", "editing"),
    list(itertools.product((False, True), repeat=3)),
)
def test_permissions_map_all_eight_policies_exactly(
    printing: bool,
    copying: bool,
    editing: bool,
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches any permission bit drifting from the three controller choices."""
    source = minimal_pdf_factory()
    sink = BytesIO()
    permissions = PdfPermissions(
        printing=printing,
        copying=copying,
        editing=editing,
    )

    build_encrypted_pdf(
        _request((source,), tmp_path / "unused.pdf", permissions), sink
    )

    with pikepdf.open(BytesIO(sink.getvalue()), password=USER_PASSWORD) as encrypted:
        allowed = encrypted.allow
        assert allowed.accessibility is True
        assert allowed.extract is copying
        assert allowed.print_lowres is printing
        assert allowed.print_highres is printing
        assert allowed.modify_annotation is editing
        assert allowed.modify_assembly is editing
        assert allowed.modify_form is editing
        assert allowed.modify_other is editing
