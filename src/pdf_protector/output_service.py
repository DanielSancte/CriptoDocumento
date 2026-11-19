"""Transactional publication and verification for encrypted PDF output."""

from __future__ import annotations

from collections.abc import Callable
import os
from pathlib import Path
import tempfile
from typing import BinaryIO

import pikepdf
from pikepdf.models.encryption import EncryptionMethod

from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    ProcessingResult,
    ProtectionRequest,
    SourcePdfError,
)
from pdf_protector.passwords import validate_pdf_password
from pdf_protector.pdf_service import build_encrypted_pdf


_SYNCED_DIRECTORY_NAMES = frozenset(
    {
        "box",
        "dropbox",
        "google drive",
        "icloud drive",
        "onedrive",
        "sharepoint",
    }
)


def is_remote_or_synced(path: Path) -> bool:
    """Heuristically identify locations which may be remote or synchronised.

    This result is advisory for the UI; it must never reject an accessible
    destination explicitly selected by the user.
    """
    text_path = str(path)
    if text_path.startswith("\\\\"):
        return True
    return any(part.casefold() in _SYNCED_DIRECTORY_NAMES for part in path.parts)


def _raise_if_cancelled(is_cancelled: Callable[[], bool]) -> None:
    if is_cancelled():
        raise CancelledError("La protección del PDF fue cancelada.")


def _validate_request_and_destination(
    request: ProtectionRequest, overwrite_confirmed: bool
) -> None:
    destination = request.destination
    if destination.suffix.casefold() != ".pdf":
        raise DestinationError("El archivo de destino debe tener extensión PDF.")
    if not destination.parent.is_dir():
        raise DestinationError("La carpeta de destino no existe.")
    if destination.exists() and not overwrite_confirmed:
        raise DestinationError("El archivo de destino ya existe y no fue confirmado.")
    for source in request.sources:
        if not source.is_file():
            raise SourcePdfError(f"No se pudo abrir el PDF de origen '{source.name}'.")


def _verify_encrypted_output(
    temporary: Path, user_password: str, expected_pages: int
) -> None:
    """Verify a completed temporary using the user's opening password."""
    try:
        with pikepdf.open(temporary, password=user_password) as encrypted:
            encryption = encrypted.encryption
            if (
                len(encrypted.pages) != expected_pages
                or encryption.bits != 256
                or encryption.R != 6
                or encryption.file_method is not EncryptionMethod.aesv3
                or encryption.stream_method is not EncryptionMethod.aesv3
                or encryption.string_method is not EncryptionMethod.aesv3
            ):
                raise DestinationError(
                    "La verificación final del PDF cifrado no fue satisfactoria."
                )
    except (OSError, pikepdf.PasswordError, pikepdf.PdfError, ValueError) as error:
        raise DestinationError(
            "No se pudo verificar el PDF protegido antes de publicarlo."
        ) from error


def _create_temporary(destination_directory: Path) -> BinaryIO:
    return tempfile.NamedTemporaryFile(
        mode="w+b",
        prefix=".pdf-protector-",
        suffix=".pdf",
        dir=destination_directory,
        delete=False,
    )


def _publish_temporary(
    temporary: Path, destination: Path, overwrite_confirmed: bool
) -> None:
    """Atomically publish an already-verified temporary on Windows.

    ``os.rename`` maps to a non-replacing Windows move and therefore claims a
    previously absent destination without a time-of-check/time-of-use gap.
    ``os.replace`` is reserved for a replacement that the caller confirmed.
    """
    if overwrite_confirmed:
        os.replace(temporary, destination)
        return
    try:
        os.rename(temporary, destination)
    except FileExistsError as error:
        raise DestinationError(
            "El archivo de destino ya existe y no fue confirmado."
        ) from error


def protect_to_destination(
    request: ProtectionRequest,
    *,
    overwrite_confirmed: bool = False,
    is_cancelled: Callable[[], bool] = lambda: False,
    on_progress: Callable[[int, int], None] | None = None,
) -> ProcessingResult:
    """Build, verify, then atomically publish an encrypted PDF destination."""
    _raise_if_cancelled(is_cancelled)
    _validate_request_and_destination(request, overwrite_confirmed)
    validate_pdf_password(request.user_password)

    temporary: Path | None = None
    try:
        try:
            with _create_temporary(request.destination.parent) as sink:
                temporary = Path(sink.name)
                pages = build_encrypted_pdf(
                    request,
                    sink,
                    is_cancelled=is_cancelled,
                    on_progress=on_progress,
                )
                sink.flush()
                os.fsync(sink.fileno())
        except OSError as error:
            raise DestinationError(
                "No se pudo escribir en la carpeta de destino seleccionada."
            ) from error

        _raise_if_cancelled(is_cancelled)
        _verify_encrypted_output(temporary, request.user_password, pages)
        _raise_if_cancelled(is_cancelled)
        _publish_temporary(temporary, request.destination, overwrite_confirmed)
        return ProcessingResult(destination=request.destination, pages=pages)
    except OSError as error:
        raise DestinationError(
            "No se pudo publicar el PDF protegido en el destino seleccionado."
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
