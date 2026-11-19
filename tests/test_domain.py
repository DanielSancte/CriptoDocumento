from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    DestinationErrorKind,
    MemoryLimitError,
    PasswordCompatibilityError,
    PdfPermissions,
    ProcessingResult,
    ProtectionError,
    ProtectionRequest,
    SourceInspection,
    SourcePdfError,
    ValidationError,
)


def test_permissions_are_immutable() -> None:
    """Catches accidental mutation of a request's permission policy."""
    permissions = PdfPermissions(printing=False, copying=False, editing=False)

    with pytest.raises(FrozenInstanceError):
        permissions.printing = True


@pytest.mark.parametrize(
    ("sources", "password"),
    [
        ((), "password"),
        ((Path("one.pdf"), Path("one.pdf")), "password"),
        ((Path("one.pdf"),), ""),
    ],
    ids=["no-sources", "duplicate-sources", "empty-password"],
)
def test_request_rejects_invalid_inputs(
    sources: tuple[Path, ...], password: str
) -> None:
    """Catches accepting a request the processing service cannot safely run."""
    with pytest.raises(ValidationError):
        ProtectionRequest(
            sources=sources,
            destination=Path("protected.pdf"),
            user_password=password,
            permissions=PdfPermissions(False, False, False),
        )


def test_request_preserves_source_order_and_hides_password_from_repr() -> None:
    """Catches reordering selected PDFs or exposing the opening password."""
    sources = (Path("second.pdf"), Path("first.pdf"))
    request = ProtectionRequest(
        sources=sources,
        destination=Path("protected.pdf"),
        user_password="not-in-repr",
        permissions=PdfPermissions(True, False, True),
    )

    assert request.sources == sources
    assert "not-in-repr" not in repr(request)


def test_domain_result_types_keep_their_declared_values() -> None:
    """Catches loss or retyping of values exchanged by domain services."""
    destination = Path("protected.pdf")
    source = Path("source.pdf")

    assert ProcessingResult(destination=destination, pages=3).pages == 3
    assert SourceInspection(path=source, pages=2, has_signatures=True).path == source


@pytest.mark.parametrize(
    "error_type",
    [
        ValidationError,
        SourcePdfError,
        PasswordCompatibilityError,
        DestinationError,
        CancelledError,
    ],
)
def test_domain_errors_share_protection_error_base(error_type: type[ProtectionError]) -> None:
    """Catches errors escaping the common protection-error handling path."""
    assert isinstance(error_type("failure"), ProtectionError)


def test_source_error_retains_the_exact_offending_path() -> None:
    """Catches diagnostics guessing the first source instead of carrying the culprit."""
    source = Path("second-source.pdf")

    error = SourcePdfError("safe source message", path=source)

    assert error.path == source
    assert str(error) == "safe source message"


@pytest.mark.parametrize("kind", list(DestinationErrorKind))
def test_destination_error_retains_its_safe_failure_category(
    kind: DestinationErrorKind,
) -> None:
    """Catches distinct destination failures collapsing before UI translation."""
    error = DestinationError("safe destination message", kind=kind)

    assert error.kind is kind
    assert str(error) == "safe destination message"


def test_memory_limit_error_uses_the_expected_error_boundary() -> None:
    """Catches memory exhaustion escaping the safe ProtectionError path."""
    assert isinstance(MemoryLimitError("memory exhausted"), ProtectionError)
