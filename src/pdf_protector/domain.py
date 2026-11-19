"""Shared domain types and errors for PDF protection workflows."""

from dataclasses import dataclass, field
from pathlib import Path


class ProtectionError(Exception):
    """Base error for expected PDF protection failures."""


class ValidationError(ProtectionError):
    """Raised when a protection request is invalid."""


class SourcePdfError(ProtectionError):
    """Raised when a source PDF cannot be inspected or processed."""


class PasswordCompatibilityError(ProtectionError):
    """Raised when a password is incompatible with PDF encryption."""


class DestinationError(ProtectionError):
    """Raised when the selected destination cannot be used."""


class CancelledError(ProtectionError):
    """Raised when PDF protection processing is cancelled."""


@dataclass(frozen=True, slots=True)
class PdfPermissions:
    printing: bool
    copying: bool
    editing: bool


@dataclass(frozen=True, slots=True)
class ProtectionRequest:
    sources: tuple[Path, ...]
    destination: Path
    user_password: str = field(repr=False)
    permissions: PdfPermissions

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValidationError("Debe seleccionar al menos un archivo PDF.")
        if len(set(self.sources)) != len(self.sources):
            raise ValidationError("No se puede seleccionar el mismo archivo más de una vez.")
        if not self.user_password:
            raise ValidationError("La contraseña no puede estar vacía.")


@dataclass(frozen=True, slots=True)
class ProcessingResult:
    destination: Path
    pages: int


@dataclass(frozen=True, slots=True)
class SourceInspection:
    path: Path
    pages: int
    has_signatures: bool
