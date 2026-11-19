"""Tests for transactional publication of protected PDF output."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pikepdf
import pytest
from pikepdf.models.encryption import EncryptionMethod

from pdf_protector import output_service
from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    PasswordCompatibilityError,
    PdfPermissions,
    ProtectionRequest,
    SourcePdfError,
)
from pdf_protector.pdf_service import build_encrypted_pdf


USER_PASSWORD = "opening-password"


def _request(source: Path, destination: Path, password: str = USER_PASSWORD) -> ProtectionRequest:
    return ProtectionRequest(
        sources=(source,),
        destination=destination,
        user_password=password,
        permissions=PdfPermissions(False, False, False),
    )


def _digest(path: Path) -> bytes:
    return hashlib.sha256(path.read_bytes()).digest()


def _temporary_outputs(directory: Path) -> list[Path]:
    return list(directory.glob(".pdf-protector-*.pdf"))


def test_rejects_a_destination_without_pdf_extension_before_creating_output(
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches publishing a protected PDF under a misleading file extension."""
    source = minimal_pdf_factory("source.pdf")
    source_digest = _digest(source)
    destination = tmp_path / "protected.txt"

    with pytest.raises(DestinationError, match="PDF"):
        output_service.protect_to_destination(_request(source, destination))

    assert not destination.exists()
    assert _digest(source) == source_digest
    assert _temporary_outputs(tmp_path) == []


def test_existing_destination_requires_explicit_overwrite_confirmation(
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches replacing a user's existing document without their confirmation."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "existing.pdf"
    destination.write_bytes(b"previous document bytes")
    source_digest = _digest(source)
    previous_digest = _digest(destination)

    with pytest.raises(DestinationError, match="ya existe"):
        output_service.protect_to_destination(_request(source, destination))

    assert _digest(source) == source_digest
    assert _digest(destination) == previous_digest
    assert _temporary_outputs(tmp_path) == []


def test_reports_an_unwritable_destination_directory_without_partial_output(
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches leaking a temporary file when the chosen directory rejects writes."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "protected.pdf"
    source_digest = _digest(source)

    def reject_temporary_file(*_args: object, **_kwargs: object) -> object:
        raise PermissionError("access denied")

    monkeypatch.setattr(output_service.tempfile, "NamedTemporaryFile", reject_temporary_file)

    with pytest.raises(DestinationError, match="carpeta de destino"):
        output_service.protect_to_destination(_request(source, destination))

    assert _digest(source) == source_digest
    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


def test_rejects_an_incompatible_password_before_creating_a_temporary_file(
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches a password encoding failure after an output file was already created."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "protected.pdf"
    source_digest = _digest(source)

    with pytest.raises(PasswordCompatibilityError):
        output_service.protect_to_destination(_request(source, destination, "\ud800"))

    assert _digest(source) == source_digest
    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (Path(r"\\server\share\protected.pdf"), True),
        (Path(r"C:\\Users\\user\\OneDrive\\protected.pdf"), True),
        (Path(r"C:\\Users\\user\\Documents\\protected.pdf"), False),
    ],
)
def test_detects_network_and_common_synced_paths_as_advisory(
    path: Path, expected: bool
) -> None:
    """Catches the UI warning heuristic missing selected remote/synced locations."""
    assert output_service.is_remote_or_synced(path) is expected


def test_missing_source_after_validation_never_publishes_a_destination(
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches publishing after a selected source disappears before it is opened."""
    source = minimal_pdf_factory("will-disappear.pdf")
    destination = tmp_path / "protected.pdf"
    original_builder = build_encrypted_pdf

    def remove_source_then_build(*args: object, **kwargs: object) -> int:
        source.unlink()
        return original_builder(*args, **kwargs)

    monkeypatch.setattr(output_service, "build_encrypted_pdf", remove_source_then_build)

    with pytest.raises(SourcePdfError, match="will-disappear.pdf"):
        output_service.protect_to_destination(_request(source, destination))

    assert not source.exists()
    assert not destination.exists()
    assert _temporary_outputs(tmp_path) == []


def test_publishes_only_a_verified_aes256_temporary_by_atomic_claim(
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches a plaintext temporary, skipped verification, or non-atomic publication."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "protected.pdf"
    source_digest = _digest(source)
    observed_temporaries: list[Path] = []
    renames: list[tuple[Path, Path]] = []
    original_rename = output_service.os.rename

    def inspect_real_temporary(*args: object, **kwargs: object) -> int:
        sink = args[1]
        pages = build_encrypted_pdf(*args, **kwargs)
        temporary = Path(sink.name)
        observed_temporaries.append(temporary)
        with pytest.raises(pikepdf.PasswordError):
            pikepdf.open(temporary, password="wrong-password")
        with pikepdf.open(temporary, password=USER_PASSWORD) as encrypted:
            assert len(encrypted.pages) == pages
            assert encrypted.encryption.bits == 256
            assert encrypted.encryption.R == 6
            assert encrypted.encryption.file_method is EncryptionMethod.aesv3
            assert encrypted.encryption.stream_method is EncryptionMethod.aesv3
            assert encrypted.encryption.string_method is EncryptionMethod.aesv3
        return pages

    def record_rename(source_path: Path, destination_path: Path) -> None:
        renames.append((Path(source_path), Path(destination_path)))
        original_rename(source_path, destination_path)

    monkeypatch.setattr(output_service, "build_encrypted_pdf", inspect_real_temporary)
    monkeypatch.setattr(output_service.os, "rename", record_rename)

    result = output_service.protect_to_destination(_request(source, destination))

    assert result.destination == destination
    assert result.pages == 1
    assert _digest(source) == source_digest
    assert renames == [(observed_temporaries[0], destination)]
    assert not observed_temporaries[0].exists()
    assert _temporary_outputs(tmp_path) == []
    with pikepdf.open(destination, password=USER_PASSWORD) as encrypted:
        assert len(encrypted.pages) == 1


def test_concurrent_destination_creation_is_not_overwritten_without_confirmation(
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches a destination created after validation being overwritten at publish."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "protected.pdf"
    source_digest = _digest(source)
    concurrent_bytes = b"created by another process"

    def build_then_create_destination(*args: object, **kwargs: object) -> int:
        pages = build_encrypted_pdf(*args, **kwargs)
        destination.write_bytes(concurrent_bytes)
        return pages

    monkeypatch.setattr(
        output_service, "build_encrypted_pdf", build_then_create_destination
    )

    with pytest.raises(DestinationError, match="ya existe"):
        output_service.protect_to_destination(_request(source, destination))

    assert _digest(source) == source_digest
    assert destination.read_bytes() == concurrent_bytes
    assert _temporary_outputs(tmp_path) == []


@pytest.mark.parametrize("failure", ["save", "verify", "cancel"])
def test_failures_leave_no_new_destination_and_preserve_an_existing_one(
    failure: str,
    minimal_pdf_factory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches failures replacing an existing destination or leaking a temporary."""
    source = minimal_pdf_factory("source.pdf")
    destination = tmp_path / "existing.pdf"
    destination.write_bytes(b"existing protected document")
    source_digest = _digest(source)
    previous_digest = _digest(destination)
    request = _request(source, destination)

    if failure == "save":
        def fail_while_saving(*_args: object, **_kwargs: object) -> int:
            raise OSError("disk full")

        monkeypatch.setattr(output_service, "build_encrypted_pdf", fail_while_saving)
        expected_error = DestinationError
        cancellation = lambda: False
    elif failure == "verify":
        def fail_verification(*_args: object, **_kwargs: object) -> None:
            raise DestinationError("La verificación final falló.")

        monkeypatch.setattr(output_service, "_verify_encrypted_output", fail_verification)
        expected_error = DestinationError
        cancellation = lambda: False
    else:
        cancellation_requested = False

        def build_then_request_cancellation(*args: object, **kwargs: object) -> int:
            nonlocal cancellation_requested
            pages = build_encrypted_pdf(*args, **kwargs)
            cancellation_requested = True
            return pages

        monkeypatch.setattr(
            output_service, "build_encrypted_pdf", build_then_request_cancellation
        )
        expected_error = CancelledError
        cancellation = lambda: cancellation_requested

    with pytest.raises(expected_error):
        output_service.protect_to_destination(
            request,
            overwrite_confirmed=True,
            is_cancelled=cancellation,
        )

    assert _digest(source) == source_digest
    assert _digest(destination) == previous_digest
    assert _temporary_outputs(tmp_path) == []
