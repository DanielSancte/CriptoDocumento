"""Qt worker that runs PDF protection without blocking the interface."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal, Slot

from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    DestinationErrorKind,
    MemoryLimitError,
    PasswordCompatibilityError,
    ProcessingResult,
    ProtectionError,
    ProtectionRequest,
    SourcePdfError,
    ValidationError,
)
from pdf_protector.output_service import protect_to_destination
from pdf_protector.pdf_service import inspect_source


class ProtectionWorker(QObject):
    """Run one protection request in a ``QThread`` and report safe outcomes."""

    progress = Signal(int, int)
    succeeded = Signal(ProcessingResult)
    failed = Signal(str)
    cancelled = Signal()
    warning = Signal(str)
    signature_confirmation_required = Signal(object)

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
        self._signature_decision = threading.Event()
        self._signature_accepted = False
        self._finished = False

    @Slot()
    def cancel(self) -> None:
        """Request cancellation from any thread.

        Connect a UI cancellation signal with ``Qt.DirectConnection`` so this
        event setter runs immediately while ``run`` occupies the worker thread.
        """
        self._cancel_event.set()
        self._signature_decision.set()

    @Slot(bool)
    def resolve_signature_confirmation(self, accepted: bool) -> None:
        """Resume preflight after the GUI confirms or declines signature loss."""
        self._signature_accepted = accepted
        self._signature_decision.set()

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

            signed_names: list[str] = []
            for path in request.sources:
                if self._cancel_event.is_set():
                    raise CancelledError("La protección del PDF fue cancelada.")
                inspection = inspect_source(
                    path, is_cancelled=self._cancel_event.is_set
                )
                if inspection.has_signatures:
                    signed_names.append(path.name)

            if signed_names:
                self.signature_confirmation_required.emit(tuple(signed_names))
                while not self._signature_decision.wait(0.05):
                    if self._cancel_event.is_set():
                        raise CancelledError("La protección del PDF fue cancelada.")
                if self._cancel_event.is_set() or not self._signature_accepted:
                    raise CancelledError("La protección del PDF fue cancelada.")

            result = protect_to_destination(
                request,
                overwrite_confirmed=self._overwrite_confirmed,
                is_cancelled=self._cancel_event.is_set,
                on_progress=self.progress.emit,
                on_warning=self.warning.emit,
            )
            self._emit_succeeded(result)
        except CancelledError:
            self._emit_cancelled()
        except ProtectionError as error:
            self._emit_failed(self._message_for(error))
        except MemoryError:
            self._emit_failed(
                "No hay memoria suficiente para procesar los documentos PDF."
            )
        except Exception:
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
            if error.path is not None:
                return f'No se pudo procesar el archivo PDF "{error.path.name}".'
            request = self._request
            if request is not None and request.sources:
                return f"No se pudo procesar el archivo PDF \"{request.sources[0].name}\"."
            return "No se pudo procesar uno de los archivos PDF seleccionados."
        if isinstance(error, PasswordCompatibilityError):
            return "La contraseña seleccionada no es compatible con el cifrado PDF."
        if isinstance(error, MemoryLimitError):
            return "No hay memoria suficiente para procesar los documentos PDF."
        if isinstance(error, DestinationError):
            if error.kind is DestinationErrorKind.DISK_FULL:
                return "No hay espacio suficiente para guardar el PDF protegido."
            if error.kind is DestinationErrorKind.UNWRITABLE:
                return "No se puede escribir en la carpeta de destino seleccionada."
            if error.kind is DestinationErrorKind.VERIFICATION:
                return "No se pudo verificar el PDF protegido antes de publicarlo."
            if error.kind is DestinationErrorKind.PUBLICATION:
                return "No se pudo publicar el PDF protegido en el destino seleccionado."
            return "No se pudo guardar el PDF protegido en el destino seleccionado."
        return "No se pudo proteger los archivos PDF seleccionados."
