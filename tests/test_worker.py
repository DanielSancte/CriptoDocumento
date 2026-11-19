"""Tests for the non-blocking PDF protection worker."""

from __future__ import annotations

from pathlib import Path
import threading
import time

import pytest
from PySide6.QtCore import QObject, QThread, Qt, Signal

from pdf_protector import worker
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


PASSWORD = "contraseña-que-no-debe-aparecer"


class _CancellationController(QObject):
    requested = Signal()


def _request(tmp_path: Path) -> ProtectionRequest:
    return ProtectionRequest(
        sources=(tmp_path / "contrato.pdf",),
        destination=tmp_path / "protegido.pdf",
        user_password=PASSWORD,
        permissions=PdfPermissions(False, False, False),
    )


@pytest.fixture(autouse=True)
def _fast_unsigned_preflight(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep worker unit tests focused while exercising the real preflight contract."""
    monkeypatch.setattr(
        worker,
        "inspect_source",
        lambda path, is_cancelled=(lambda: False): SourceInspection(
            path=path, pages=1, has_signatures=False
        ),
        raising=False,
    )


def test_worker_emits_result_and_monotonic_progress_from_the_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches dropping the service result or reordering its progress updates."""
    request = _request(tmp_path)
    result = ProcessingResult(destination=request.destination, pages=3)
    observed_progress: list[tuple[int, int]] = []
    observed_results: list[ProcessingResult] = []

    def complete(
        received: ProtectionRequest, **kwargs: object
    ) -> ProcessingResult:
        assert received is request
        on_progress = kwargs["on_progress"]
        assert callable(on_progress)
        on_progress(1, 3)
        on_progress(2, 3)
        on_progress(3, 3)
        return result

    monkeypatch.setattr(worker, "protect_to_destination", complete)
    processor = worker.ProtectionWorker(request)
    processor.progress.connect(
        lambda completed, total: observed_progress.append((completed, total))
    )
    processor.succeeded.connect(observed_results.append)

    processor.run()

    assert observed_progress == [(1, 3), (2, 3), (3, 3)]
    assert observed_results == [result]


@pytest.mark.parametrize(
    ("error", "expected_text"),
    [
        (ProtectionError("detalles internos"), "No se pudo proteger los archivos PDF"),
        (ValidationError("detalles internos"), "solicitud"),
        (SourcePdfError("detalles internos"), "contrato.pdf"),
        (PasswordCompatibilityError("detalles internos"), "contraseña"),
        (DestinationError("detalles internos"), "destino"),
    ],
    ids=["generic-protection", "validation", "source", "password", "destination"],
)
def test_worker_translates_expected_errors_without_exposing_sensitive_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error: Exception,
    expected_text: str,
) -> None:
    """Catches leaking service details or a password through a failure signal."""
    messages: list[str] = []

    def fail(*_args: object, **_kwargs: object) -> ProcessingResult:
        raise error

    monkeypatch.setattr(worker, "protect_to_destination", fail)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.failed.connect(messages.append)

    processor.run()

    assert len(messages) == 1
    assert expected_text.casefold() in messages[0].casefold()
    assert "detalles internos" not in messages[0]
    assert PASSWORD not in messages[0]


def test_worker_emits_safe_generic_message_for_unexpected_exception(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches exposing exception details, file contents, or passwords unexpectedly."""
    messages: list[str] = []

    def crash(*_args: object, **_kwargs: object) -> ProcessingResult:
        raise RuntimeError(f"traza interna {PASSWORD} contenido confidencial")

    monkeypatch.setattr(worker, "protect_to_destination", crash)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.failed.connect(messages.append)

    processor.run()

    assert messages == ["Ocurrió un problema inesperado al proteger los archivos PDF."]


def test_worker_cancelled_before_run_emits_only_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches starting the service after a user has already cancelled it."""
    calls = 0
    cancelled = 0
    failures: list[str] = []
    successes: list[ProcessingResult] = []

    def should_not_run(*_args: object, **_kwargs: object) -> ProcessingResult:
        nonlocal calls
        calls += 1
        raise AssertionError("the service must not run after cancellation")

    monkeypatch.setattr(worker, "protect_to_destination", should_not_run)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.cancelled.connect(lambda: _increment_cancelled())
    processor.failed.connect(failures.append)
    processor.succeeded.connect(successes.append)

    def _increment_cancelled() -> None:
        nonlocal cancelled
        cancelled += 1

    processor.cancel()
    processor.run()

    assert calls == 0
    assert cancelled == 1
    assert failures == []
    assert successes == []


def test_worker_cancellation_observed_by_service_emits_only_cancelled(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches reporting a failure or success after the service observes cancellation."""
    cancelled = 0
    failures: list[str] = []
    successes: list[ProcessingResult] = []

    processor = worker.ProtectionWorker(_request(tmp_path))

    def cancel_during_service(*_args: object, **kwargs: object) -> ProcessingResult:
        is_cancelled = kwargs["is_cancelled"]
        assert callable(is_cancelled)
        processor.cancel()
        if is_cancelled():
            raise CancelledError("never expose this detail")
        raise AssertionError("the cancellation predicate was not passed through")

    monkeypatch.setattr(worker, "protect_to_destination", cancel_during_service)

    def _increment_cancelled() -> None:
        nonlocal cancelled
        cancelled += 1

    processor.cancelled.connect(_increment_cancelled)
    processor.failed.connect(failures.append)
    processor.succeeded.connect(successes.append)

    processor.run()

    assert cancelled == 1
    assert failures == []
    assert successes == []


def test_worker_cancelled_from_main_thread_while_running_in_qthread(
    monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path
) -> None:
    """Catches queueing cancellation behind a blocking worker operation."""
    service_started = threading.Event()
    terminal_signals: list[str] = []
    processor = worker.ProtectionWorker(_request(tmp_path))
    thread = QThread()
    controller = _CancellationController()

    def wait_for_cancellation(*_args: object, **kwargs: object) -> ProcessingResult:
        is_cancelled = kwargs["is_cancelled"]
        assert callable(is_cancelled)
        service_started.set()
        while not is_cancelled():
            time.sleep(0.001)
        raise CancelledError("never expose this detail")

    monkeypatch.setattr(worker, "protect_to_destination", wait_for_cancellation)
    processor.moveToThread(thread)
    thread.started.connect(processor.run)
    thread.finished.connect(processor.deleteLater)
    controller.requested.connect(processor.cancel, Qt.ConnectionType.DirectConnection)
    processor.cancelled.connect(lambda: terminal_signals.append("cancelled"))
    processor.succeeded.connect(lambda _result: terminal_signals.append("succeeded"))
    processor.failed.connect(lambda _message: terminal_signals.append("failed"))
    processor.cancelled.connect(thread.quit)

    with qtbot.waitSignal(thread.finished, timeout=1_000):
        thread.start()
        qtbot.waitUntil(service_started.is_set, timeout=1_000)
        controller.requested.emit()

    assert not thread.isRunning()
    assert terminal_signals == ["cancelled"]


def test_worker_marks_success_finished_before_signal_allows_reentrant_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches a reentrant terminal-signal handler starting the request twice."""
    request = _request(tmp_path)
    result = ProcessingResult(destination=request.destination, pages=1)
    calls = 0
    reentered = False
    results: list[ProcessingResult] = []
    processor = worker.ProtectionWorker(request)

    def complete(*_args: object, **_kwargs: object) -> ProcessingResult:
        nonlocal calls
        calls += 1
        return result

    def run_once_more() -> None:
        nonlocal reentered
        if not reentered:
            reentered = True
            processor.run()

    monkeypatch.setattr(worker, "protect_to_destination", complete)
    processor.succeeded.connect(run_once_more)
    processor.succeeded.connect(results.append)

    processor.run()

    assert calls == 1
    assert results == [result]


def test_worker_reports_success_when_cancellation_arrives_after_commit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches a late cancellation relabeling an already committed result."""
    request = _request(tmp_path)
    result = ProcessingResult(destination=request.destination, pages=1)
    processor = worker.ProtectionWorker(request)
    terminals: list[str] = []

    def commit_then_cancel(*_args: object, **_kwargs: object) -> ProcessingResult:
        processor.cancel()
        return result

    monkeypatch.setattr(worker, "protect_to_destination", commit_then_cancel)
    processor.succeeded.connect(lambda _result: terminals.append("succeeded"))
    processor.cancelled.connect(lambda: terminals.append("cancelled"))
    processor.failed.connect(lambda _message: terminals.append("failed"))

    processor.run()

    assert terminals == ["succeeded"]


def test_worker_uses_the_structured_second_source_path_in_diagnostics(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches source diagnostics always naming the first selected PDF."""
    first = tmp_path / "primero.pdf"
    second = tmp_path / "segundo.pdf"
    request = ProtectionRequest(
        sources=(first, second),
        destination=tmp_path / "protegido.pdf",
        user_password=PASSWORD,
        permissions=PdfPermissions(False, False, False),
    )
    messages: list[str] = []

    def fail_on_second(*_args: object, **_kwargs: object) -> ProcessingResult:
        raise SourcePdfError("internal source detail", path=second)

    monkeypatch.setattr(worker, "protect_to_destination", fail_on_second)
    processor = worker.ProtectionWorker(request)
    processor.failed.connect(messages.append)

    processor.run()

    assert len(messages) == 1
    assert second.name in messages[0]
    assert first.name not in messages[0]
    assert "internal source detail" not in messages[0]
    assert PASSWORD not in messages[0]


@pytest.mark.parametrize(
    ("kind", "expected_text"),
    [
        (DestinationErrorKind.DISK_FULL, "espacio"),
        (DestinationErrorKind.UNWRITABLE, "escribir"),
        (DestinationErrorKind.VERIFICATION, "verificar"),
        (DestinationErrorKind.PUBLICATION, "publicar"),
    ],
)
def test_worker_preserves_actionable_destination_categories_without_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kind: DestinationErrorKind,
    expected_text: str,
) -> None:
    """Catches every destination failure collapsing into one generic message."""
    messages: list[str] = []

    def fail(*_args: object, **_kwargs: object) -> ProcessingResult:
        raise DestinationError("internal destination detail", kind=kind)

    monkeypatch.setattr(worker, "protect_to_destination", fail)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.failed.connect(messages.append)

    processor.run()

    assert len(messages) == 1
    assert expected_text in messages[0].casefold()
    assert "internal destination detail" not in messages[0]
    assert PASSWORD not in messages[0]


def test_worker_translates_raw_memory_exhaustion_to_safe_spanish_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches memory exhaustion exposing exception details or a traceback."""
    secret = f"allocation detail {PASSWORD}"
    messages: list[str] = []

    def exhaust_memory(*_args: object, **_kwargs: object) -> SourceInspection:
        raise MemoryError(secret)

    monkeypatch.setattr(worker, "inspect_source", exhaust_memory)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.failed.connect(messages.append)

    processor.run()

    assert len(messages) == 1
    assert "memoria" in messages[0].casefold()
    assert secret not in messages[0]
    assert PASSWORD not in messages[0]


def test_worker_surfaces_cleanup_warning_without_replacing_primary_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches cleanup warnings being dropped or replacing the main error."""
    warnings: list[str] = []
    failures: list[str] = []
    safe_warning = "No se pudo eliminar un archivo temporal de forma automática."

    def fail_with_warning(*_args: object, **kwargs: object) -> ProcessingResult:
        on_warning = kwargs["on_warning"]
        assert callable(on_warning)
        on_warning(safe_warning)
        raise DestinationError(
            "internal publish detail", kind=DestinationErrorKind.PUBLICATION
        )

    monkeypatch.setattr(worker, "protect_to_destination", fail_with_warning)
    processor = worker.ProtectionWorker(_request(tmp_path))
    processor.warning.connect(warnings.append)
    processor.failed.connect(failures.append)

    processor.run()

    assert warnings == [safe_warning]
    assert len(failures) == 1
    assert "publicar" in failures[0].casefold()


def test_worker_requires_signature_consent_before_output_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches processing signed input before the user confirms invalidation."""
    request = _request(tmp_path)
    result = ProcessingResult(destination=request.destination, pages=1)
    events: list[str] = []

    def signed_inspection(path: Path, **_kwargs: object) -> SourceInspection:
        events.append("inspect")
        return SourceInspection(path=path, pages=1, has_signatures=True)

    def protect(*_args: object, **_kwargs: object) -> ProcessingResult:
        events.append("protect")
        return result

    monkeypatch.setattr(worker, "inspect_source", signed_inspection)
    monkeypatch.setattr(worker, "protect_to_destination", protect)
    processor = worker.ProtectionWorker(request)

    def confirm(names: tuple[str, ...]) -> None:
        events.append("confirm")
        assert names == (request.sources[0].name,)
        processor.resolve_signature_confirmation(True)

    processor.signature_confirmation_required.connect(confirm)

    processor.run()

    assert events == ["inspect", "confirm", "protect"]


def test_worker_signature_decline_cancels_before_output_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches declining the signature warning while processing still starts."""
    request = _request(tmp_path)
    terminals: list[str] = []
    monkeypatch.setattr(
        worker,
        "inspect_source",
        lambda path, **_kwargs: SourceInspection(
            path=path, pages=1, has_signatures=True
        ),
    )
    monkeypatch.setattr(
        worker,
        "protect_to_destination",
        lambda *_args, **_kwargs: pytest.fail(
            "output service must not run after signature consent is declined"
        ),
    )
    processor = worker.ProtectionWorker(request)
    processor.signature_confirmation_required.connect(
        lambda _names: processor.resolve_signature_confirmation(False)
    )
    processor.cancelled.connect(lambda: terminals.append("cancelled"))

    processor.run()

    assert terminals == ["cancelled"]
