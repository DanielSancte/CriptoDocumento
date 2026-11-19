"""Transactional publication and verification for encrypted PDF output."""

from __future__ import annotations

from collections.abc import Callable
import ctypes
import errno
import os
from pathlib import Path
import tempfile
from typing import BinaryIO

import pikepdf
from pikepdf.models.encryption import EncryptionMethod

from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    DestinationErrorKind,
    MemoryLimitError,
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
_REMOTE_DRIVE = 4
_CLEANUP_WARNING = "No se pudo eliminar un archivo temporal de forma automática."


def _windows_drive_type(path: Path) -> int | None:
    """Return Windows' drive type for a rooted drive path when available."""
    if os.name != "nt":
        return None
    text_path = str(path).replace("/", "\\")
    if text_path.casefold().startswith("\\\\?\\unc\\"):
        return _REMOTE_DRIVE
    if text_path.casefold().startswith("\\\\?\\"):
        text_path = text_path[4:]
    drive = Path(text_path).drive
    if len(drive) != 2 or drive[1] != ":":
        return None
    try:
        return int(ctypes.windll.kernel32.GetDriveTypeW(f"{drive}\\"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None


def is_remote_or_synced(path: Path) -> bool:
    """Heuristically identify locations which may be remote or synchronised.

    This result is advisory for the UI; it must never reject an accessible
    destination explicitly selected by the user.
    """
    text_path = str(path).replace("/", "\\")
    folded_path = text_path.casefold()
    if folded_path.startswith("\\\\?\\unc\\"):
        return True
    if folded_path.startswith("\\\\") and not folded_path.startswith("\\\\?\\"):
        return True
    for part in path.parts:
        folded_part = part.casefold()
        if folded_part in _SYNCED_DIRECTORY_NAMES or folded_part.startswith(
            ("onedrive - ", "onedrive – ", "onedrive — ")
        ):
            return True
    return _windows_drive_type(path) == _REMOTE_DRIVE


def _raise_if_cancelled(is_cancelled: Callable[[], bool]) -> None:
    if is_cancelled():
        raise CancelledError("La protección del PDF fue cancelada.")


def _validate_request_and_destination(
    request: ProtectionRequest, overwrite_confirmed: bool
) -> None:
    destination = request.destination
    if destination.suffix.casefold() != ".pdf":
        raise DestinationError(
            "El archivo de destino debe tener extensión PDF.",
            kind=DestinationErrorKind.INVALID,
        )
    if not destination.parent.is_dir():
        raise DestinationError(
            "La carpeta de destino no existe.", kind=DestinationErrorKind.INVALID
        )
    if destination.exists() and not overwrite_confirmed:
        raise DestinationError(
            "El archivo de destino ya existe y no fue confirmado.",
            kind=DestinationErrorKind.INVALID,
        )
    for source in request.sources:
        if not source.is_file():
            raise SourcePdfError(
                f"No se pudo abrir el PDF de origen '{source.name}'.", path=source
            )


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
                    "La verificación final del PDF cifrado no fue satisfactoria.",
                    kind=DestinationErrorKind.VERIFICATION,
                )
    except (OSError, pikepdf.PasswordError, pikepdf.PdfError, ValueError) as error:
        raise DestinationError(
            "No se pudo verificar el PDF protegido antes de publicarlo.",
            kind=DestinationErrorKind.VERIFICATION,
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
            "El archivo de destino ya existe y no fue confirmado.",
            kind=DestinationErrorKind.INVALID,
        ) from error


def _kind_for_os_error(
    error: OSError,
    *,
    default: DestinationErrorKind,
) -> DestinationErrorKind:
    if error.errno == errno.ENOSPC or getattr(error, "winerror", None) == 112:
        return DestinationErrorKind.DISK_FULL
    if isinstance(error, PermissionError) or error.errno in {
        errno.EACCES,
        errno.EPERM,
        errno.EROFS,
    }:
        return DestinationErrorKind.UNWRITABLE
    return default


def _destination_error_from_os(
    error: OSError,
    *,
    default: DestinationErrorKind,
) -> DestinationError:
    kind = _kind_for_os_error(error, default=default)
    if kind is DestinationErrorKind.DISK_FULL:
        message = "No hay espacio suficiente para crear el PDF protegido."
    elif kind is DestinationErrorKind.UNWRITABLE:
        message = "No se puede escribir en la carpeta de destino seleccionada."
    elif kind is DestinationErrorKind.PUBLICATION:
        message = "No se pudo publicar el PDF protegido en el destino seleccionado."
    else:
        message = "No se pudo escribir el PDF protegido en el destino seleccionado."
    return DestinationError(message, kind=kind)


def _report_cleanup_warning(on_warning: Callable[[str], None] | None) -> None:
    if on_warning is None:
        return
    try:
        on_warning(_CLEANUP_WARNING)
    except Exception:
        # A reporting callback must never replace the primary processing result.
        return


def protect_to_destination(
    request: ProtectionRequest,
    *,
    overwrite_confirmed: bool = False,
    is_cancelled: Callable[[], bool] = lambda: False,
    on_progress: Callable[[int, int], None] | None = None,
    on_warning: Callable[[str], None] | None = None,
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
            raise _destination_error_from_os(
                error, default=DestinationErrorKind.UNWRITABLE
            ) from error
        except MemoryError as error:
            raise MemoryLimitError(
                "No hay memoria suficiente para procesar los documentos PDF."
            ) from error

        _raise_if_cancelled(is_cancelled)
        _verify_encrypted_output(temporary, request.user_password, pages)
        _raise_if_cancelled(is_cancelled)
        _publish_temporary(temporary, request.destination, overwrite_confirmed)
        return ProcessingResult(destination=request.destination, pages=pages)
    except OSError as error:
        raise _destination_error_from_os(
            error, default=DestinationErrorKind.PUBLICATION
        ) from error
    except MemoryError as error:
        raise MemoryLimitError(
            "No hay memoria suficiente para procesar los documentos PDF."
        ) from error
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                _report_cleanup_warning(on_warning)
