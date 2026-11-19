"""Qt worker that runs PDF protection without blocking the interface."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    PasswordCompatibilityError,
    ProcessingResult,
    ProtectionError,
    ProtectionRequest,
    SourcePdfError,
    ValidationError,
)
from pdf_protector.output_service import protect_to_destination


class ProtectionWorker(QObject):
    """Run one protection request in a ``QThread`` and report safe outcomes."""

    progress = Signal(int, int)
    succeeded = Signal(ProcessingResult)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(
        self,
        request: ProtectionRequest,
        *,
        overwrite_confirmed: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._request: ProtectionRequest | None = request
        self._overwrite_confirmed = overwrite_confirmed
        self._cancel_event = threading.Event()
        self._finished = False

    @Slot()
    def cancel(self) -> None:
        """Request cancellation from any thread.

        Connect a UI cancellation signal with ``Qt.DirectConnection`` so this
        event setter runs immediately while ``run`` occupies the worker thread.
        """
        self._cancel_event.set()

    @Slot()
    def run(self) -> None:
        """Protect the request and emit exactly one terminal outcome."""
        if self._finished:
            return

        try:
            request = self._request
            if request is None or self._cancel_event.is_set():
                self._emit_cancelled()
                return

            result = protect_to_destination(
                request,
                overwrite_confirmed=self._overwrite_confirmed,
                is_cancelled=self._cancel_event.is_set,
                on_progress=self.progress.emit,
            )
            if self._cancel_event.is_set():
                self._emit_cancelled()
            else:
                self._emit_succeeded(result)
        except CancelledError:
            self._emit_cancelled()
        except ProtectionError as error:
            if self._cancel_event.is_set():
                self._emit_cancelled()
            else:
                self._emit_failed(self._message_for(error))
        except Exception:
            if self._cancel_event.is_set():
                self._emit_cancelled()
            else:
                self._emit_failed(
                    "Ocurrió un problema inesperado al proteger los archivos PDF."
                )
        finally:
            self._request = None

    def _emit_cancelled(self) -> None:
        if not self._finished:
            self._finished = True
            self.cancelled.emit()

    def _emit_succeeded(self, result: ProcessingResult) -> None:
        if not self._finished:
            self._finished = True
            self.succeeded.emit(result)

    def _emit_failed(self, message: str) -> None:
        if not self._finished:
            self._finished = True
            self.failed.emit(message)

    def _message_for(
        self,
        error: ProtectionError,
    ) -> str:
        if isinstance(error, ValidationError):
            return "La solicitud de protección no es válida."
        if isinstance(error, SourcePdfError):
            request = self._request
            if request is not None and request.sources:
                return f"No se pudo procesar el archivo PDF \"{request.sources[0].name}\"."
            return "No se pudo procesar uno de los archivos PDF seleccionados."
        if isinstance(error, PasswordCompatibilityError):
            return "La contraseña seleccionada no es compatible con el cifrado PDF."
        if isinstance(error, DestinationError):
            return "No se pudo guardar el PDF protegido en el destino seleccionado."
        return "No se pudo proteger los archivos PDF seleccionados."
