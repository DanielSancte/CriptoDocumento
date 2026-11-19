"""Tests for the non-blocking PDF protection worker."""

from __future__ import annotations

from pathlib import Path

import pytest

from pdf_protector import worker
from pdf_protector.domain import (
    CancelledError,
    DestinationError,
    PasswordCompatibilityError,
    PdfPermissions,
    ProcessingResult,
    ProtectionError,
    ProtectionRequest,
    SourcePdfError,
    ValidationError,
)


PASSWORD = "contraseña-que-no-debe-aparecer"


def _request(tmp_path: Path) -> ProtectionRequest:
    return ProtectionRequest(
        sources=(tmp_path / "contrato.pdf",),
        destination=tmp_path / "protegido.pdf",
        user_password=PASSWORD,
        permissions=PdfPermissions(False, False, False),
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
