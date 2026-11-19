"""Tests for secure, literal PDF password handling."""

from __future__ import annotations

import pikepdf
import pytest

from pdf_protector import passwords
from pdf_protector.domain import PasswordCompatibilityError


def test_owner_password_requests_256_bits_from_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches weakening the random administrative password below 256 bits."""
    requested_bytes: list[int] = []

    def token_urlsafe(number_bytes: int) -> str:
        requested_bytes.append(number_bytes)
        return "administrative-randomness"

    monkeypatch.setattr(passwords.secrets, "token_urlsafe", token_urlsafe)

    assert passwords.generate_owner_password() == "administrative-randomness"
    assert requested_bytes == [32]


def test_owner_passwords_are_distinct() -> None:
    """Catches returning a fixed administrative password across documents."""
    assert passwords.generate_owner_password() != passwords.generate_owner_password()


@pytest.mark.parametrize(
    ("password", "confirmation"),
    [
        ("", ""),
        ("clave-uno", "clave-dos"),
    ],
    ids=["empty", "mismatch"],
)
def test_password_pair_rejects_empty_or_different_values(
    password: str, confirmation: str
) -> None:
    """Catches accepting unusable or differently confirmed opening passwords."""
    with pytest.raises(PasswordCompatibilityError):
        passwords.validate_password_pair(password, confirmation)


def test_password_validation_passes_spaces_and_unicode_to_qpdf_literally(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches trimming, normalizing, or otherwise changing the user's password."""
    password = " \u00a0clave\U0001f642\t"
    received_by_qpdf: list[str] = []
    real_encryption = pikepdf.Encryption

    def capture_encryption(*args: object, **kwargs: object) -> pikepdf.Encryption:
        received_by_qpdf.append(kwargs["user"])
        return real_encryption(*args, **kwargs)

    monkeypatch.setattr(passwords.pikepdf, "Encryption", capture_encryption)

    assert passwords.validate_password_pair(password, password) is None
    assert passwords.validate_pdf_password(password) is None
    assert received_by_qpdf == [password]


def test_password_qpdf_rejects_raises_compatibility_error() -> None:
    """Catches silently changing a password qpdf cannot encode in an AES-256 PDF."""
    with pytest.raises(PasswordCompatibilityError):
        passwords.validate_pdf_password("before\x00after")


def test_password_with_unpaired_surrogate_raises_compatibility_error() -> None:
    """Catches qpdf runtime failures leaking past the compatibility boundary."""
    with pytest.raises(PasswordCompatibilityError):
        passwords.validate_pdf_password(chr(0xD800))
