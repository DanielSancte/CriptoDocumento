"""Secure password generation and PDF compatibility checks."""

from __future__ import annotations

from io import BytesIO
import secrets

import pikepdf

from pdf_protector.domain import PasswordCompatibilityError


def generate_owner_password() -> str:
    """Generate a one-use administrative password with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def validate_password_pair(password: str, confirmation: str) -> None:
    """Reject empty or differently confirmed opening passwords literally."""
    if not password:
        raise PasswordCompatibilityError("La contraseña no puede estar vacía.")
    if password != confirmation:
        raise PasswordCompatibilityError("Las contraseñas no coinciden.")


def validate_pdf_password(password: str) -> None:
    """Ensure qpdf can encode the exact password in an AES-256 PDF in memory."""
    try:
        with pikepdf.Pdf.new() as document:
            document.save(
                BytesIO(),
                encryption=pikepdf.Encryption(
                    user=password,
                    owner=generate_owner_password(),
                    R=6,
                    aes=True,
                    metadata=True,
                ),
            )
    except (pikepdf.PdfError, ValueError) as error:
        raise PasswordCompatibilityError(
            "La contraseña no es compatible con el cifrado PDF AES-256."
        ) from error
