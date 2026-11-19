"""Behavioral tests for the complete Spanish desktop workflow."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import threading
import time

import pytest
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import QLineEdit

from pdf_protector import main_window
from pdf_protector.domain import ProcessingResult, SourceInspection
from pdf_protector.main_window import MainWindow


PASSWORD = "Una contraseña segura 2026"


def _displayed_names(window: MainWindow) -> list[str]:
    return [
        window.files_model.item(row).text()
        for row in range(window.files_model.rowCount())
    ]


def _make_window(qtbot) -> MainWindow:
    window = MainWindow()
    qtbot.addWidget(window)
    window.show()
    return window


def _fill_valid_form(window: MainWindow, source: Path) -> None:
    window.add_sources([source])
    window.password_edit.setText(PASSWORD)
    window.confirmation_edit.setText(PASSWORD)


def _worker_type(
    outcome: str,
    *,
    progress: tuple[int, int] | None = None,
    blocking: bool = False,
) -> type[QObject]:
    """Return a complete Worker-interface fake; PDF execution is tested elsewhere."""

    class FakeWorker(QObject):
        progress = Signal(int, int)
        succeeded = Signal(ProcessingResult)
        failed = Signal(str)
        cancelled = Signal()

        instances: list["FakeWorker"] = []
        started = threading.Event()
        release = threading.Event()

        def __init__(
            self,
            request,
            *,
            overwrite_confirmed: bool = False,
            parent: QObject | None = None,
        ) -> None:
            super().__init__(parent)
            self.request = request
            self.overwrite_confirmed = overwrite_confirmed
            self.cancel_thread: QThread | None = None
            self.cancel_native_thread: int | None = None
            type(self).instances.append(self)

        @Slot()
        def run(self) -> None:
            if progress is not None:
                self.progress.emit(*progress)
            type(self).started.set()
            if blocking:
                while not type(self).release.wait(0.002):
                    time.sleep(0.001)

            if outcome == "success":
                self.succeeded.emit(
                    ProcessingResult(destination=self.request.destination, pages=2)
                )
            elif outcome == "failure":
                self.failed.emit("No se pudo guardar el PDF protegido.")
            else:
                self.cancelled.emit()

        @Slot()
        def cancel(self) -> None:
            self.cancel_thread = QThread.currentThread()
            self.cancel_native_thread = threading.get_ident()
            type(self).release.set()

    return FakeWorker


def test_selection_keeps_paths_and_order_while_reporting_invalid_and_duplicate_entries(
    qtbot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Catches exposing paths, accepting non-PDFs, duplicates, or reordering."""
    first = tmp_path / "Informe.PDF"
    second = tmp_path / "anexo.pdf"
    other = tmp_path / "notas.txt"
    for path in (first, second, other):
        path.write_bytes(b"fixture")
    window = _make_window(qtbot)
    messages: list[str] = []
    monkeypatch.setattr(
        window,
        "_show_information",
        lambda _title, text: messages.append(text),
    )

    window.add_sources(
        [first, other, first, Path(str(first).swapcase()), second]
    )

    assert window.source_paths() == (first.resolve(), second.resolve())
    assert _displayed_names(window) == [first.name, second.name]
    assert all(str(tmp_path) not in name for name in _displayed_names(window))
    assert any("PDF" in message for message in messages)
    assert any("seleccionado" in message.casefold() for message in messages)


def test_move_and_remove_preserve_stable_order_without_deleting_sources(
    qtbot, tmp_path: Path
) -> None:
    """Catches unstable ordering or a remove action deleting an original file."""
    sources = tuple(tmp_path / name for name in ("uno.pdf", "dos.pdf", "tres.pdf"))
    for source in sources:
        source.write_bytes(b"original")
    window = _make_window(qtbot)
    window.add_sources(sources)

    window.files_view.setCurrentIndex(window.files_model.index(1, 0))
    qtbot.mouseClick(window.move_up_button, Qt.MouseButton.LeftButton)
    assert window.source_paths() == (sources[1], sources[0], sources[2])

    qtbot.mouseClick(window.move_down_button, Qt.MouseButton.LeftButton)
    assert window.source_paths() == sources

    qtbot.mouseClick(window.remove_button, Qt.MouseButton.LeftButton)
    assert window.source_paths() == (sources[0], sources[2])
    assert all(source.read_bytes() == b"original" for source in sources)


def test_source_that_disappears_after_selection_is_reported_before_save_dialog(
    qtbot, monkeypatch: pytest.MonkeyPatch, minimal_pdf_factory
) -> None:
    """Catches starting a job after a selected source was removed externally."""
    source = minimal_pdf_factory("desaparece.pdf")
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    source.unlink()
    warnings: list[str] = []
    monkeypatch.setattr(
        window, "_show_warning", lambda _title, text: warnings.append(text)
    )
    monkeypatch.setattr(
        window,
        "_choose_destination",
        lambda: pytest.fail("save dialog must not open for a missing source"),
    )

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)

    assert warnings and source.name in warnings[0]
    assert window._thread is None


def test_form_defaults_labels_accessibility_and_keyboard_focus(qtbot) -> None:
    """Catches permissive defaults, inaccessible labels, or mouse-only controls."""
    window = _make_window(qtbot)

    assert [
        window.printing_checkbox.text(),
        window.copying_checkbox.text(),
        window.editing_checkbox.text(),
    ] == [
        "Permitir impresión",
        "Permitir copiar contenido",
        "Permitir edición",
    ]
    assert not window.printing_checkbox.isChecked()
    assert not window.copying_checkbox.isChecked()
    assert not window.editing_checkbox.isChecked()
    assert window.password_label.buddy() is window.password_edit
    assert window.confirmation_label.buddy() is window.confirmation_edit

    controls = (
        window.add_button,
        window.files_view,
        window.move_up_button,
        window.move_down_button,
        window.remove_button,
        window.password_edit,
        window.confirmation_edit,
        window.show_password_button,
        window.printing_checkbox,
        window.copying_checkbox,
        window.editing_checkbox,
        window.create_button,
    )
    for control in controls:
        assert control.accessibleName()
        assert control.focusPolicy() & Qt.FocusPolicy.TabFocus


def test_passwords_are_hidden_toggle_together_and_gate_submission(
    qtbot, tmp_path: Path
) -> None:
    """Catches secret exposure or enabling submission with invalid form state."""
    source = tmp_path / "entrada.pdf"
    source.write_bytes(b"fixture")
    window = _make_window(qtbot)

    assert window.password_edit.echoMode() == QLineEdit.EchoMode.Password
    assert window.confirmation_edit.echoMode() == QLineEdit.EchoMode.Password
    assert not window.create_button.isEnabled()

    window.add_sources([source])
    window.password_edit.setText("uno")
    window.confirmation_edit.setText("otro")
    assert not window.create_button.isEnabled()

    window.confirmation_edit.setText("uno")
    assert window.create_button.isEnabled()
    qtbot.mouseClick(window.show_password_button, Qt.MouseButton.LeftButton)
    assert window.password_edit.echoMode() == QLineEdit.EchoMode.Normal
    assert window.confirmation_edit.echoMode() == QLineEdit.EchoMode.Normal
    assert "Ocultar" in window.show_password_button.text()

    qtbot.mouseClick(window.show_password_button, Qt.MouseButton.LeftButton)
    assert window.password_edit.echoMode() == QLineEdit.EchoMode.Password
    assert window.confirmation_edit.echoMode() == QLineEdit.EchoMode.Password

    window.files_view.setCurrentIndex(window.files_model.index(0, 0))
    qtbot.mouseClick(window.remove_button, Qt.MouseButton.LeftButton)
    assert not window.create_button.isEnabled()


def test_cancelled_save_dialog_does_not_start_or_change_files(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
) -> None:
    """Catches processing after the user cancels destination selection."""
    source = minimal_pdf_factory("entrada.pdf")
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: None)
    NeverWorker = _worker_type("success")
    monkeypatch.setattr(main_window, "ProtectionWorker", NeverWorker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)

    assert NeverWorker.instances == []
    assert source.exists()
    assert window.password_edit.text() == PASSWORD


def test_signature_warning_is_confirmed_before_destination_selection(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
) -> None:
    """Catches silently invalidating a source signature or warning too late."""
    source = minimal_pdf_factory("firmado.pdf")
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(
        main_window,
        "inspect_source",
        lambda path: SourceInspection(path=path, pages=1, has_signatures=True),
    )
    confirmations: list[str] = []
    monkeypatch.setattr(
        window,
        "_confirm",
        lambda _title, text: confirmations.append(text) or False,
    )
    monkeypatch.setattr(
        window,
        "_choose_destination",
        lambda: pytest.fail("signature warning must precede save dialog"),
    )

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)

    assert len(confirmations) == 1
    assert "firma" in confirmations[0].casefold()
    assert source.name in confirmations[0]
    assert window._thread is None


def test_route_warning_then_overwrite_confirmation_precede_worker(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches bypassing route/overwrite consent or giving the worker wrong policy."""
    source = minimal_pdf_factory("entrada.pdf")
    synced = tmp_path / "OneDrive"
    synced.mkdir()
    destination = synced / "salida.pdf"
    destination.write_bytes(b"existing")
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    window.printing_checkbox.setChecked(True)
    monkeypatch.setattr(window, "_choose_destination", lambda: destination)
    confirmations: list[str] = []
    monkeypatch.setattr(
        window,
        "_confirm",
        lambda _title, text: confirmations.append(text) or True,
    )
    monkeypatch.setattr(window, "_ask_open_folder", lambda _result: False)
    Worker = _worker_type("success")
    monkeypatch.setattr(main_window, "ProtectionWorker", Worker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window._thread is None, timeout=1_000)

    assert "sincron" in confirmations[0].casefold()
    assert "existe" in confirmations[1].casefold()
    assert len(Worker.instances) == 1
    processor = Worker.instances[0]
    assert processor.overwrite_confirmed is True
    assert processor.request.sources == (source.resolve(),)
    assert processor.request.destination == destination
    assert processor.request.permissions.printing is True


def test_destination_default_name_is_documentos_protegidos(qtbot) -> None:
    """Catches presenting an unrelated or extensionless default output name."""
    window = _make_window(qtbot)

    default = window.default_destination()

    assert default.name == "documentos_protegidos.pdf"
    assert default.is_absolute()


def test_destination_cannot_replace_a_selected_original(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
) -> None:
    """Catches using an original source path as the published destination."""
    source = minimal_pdf_factory("original.pdf")
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: source)
    warnings: list[str] = []
    monkeypatch.setattr(
        window, "_show_warning", lambda _title, text: warnings.append(text)
    )
    NeverWorker = _worker_type("success")
    monkeypatch.setattr(main_window, "ProtectionWorker", NeverWorker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)

    assert warnings and "original" in warnings[0].casefold()
    assert NeverWorker.instances == []
    assert source.exists()


def test_progress_and_cancel_use_direct_connection_and_lock_mutations(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches queued cancellation behind run or edits during an active job."""
    source = minimal_pdf_factory("entrada.pdf")
    destination = tmp_path / "salida.pdf"
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: destination)
    monkeypatch.setattr(main_window, "is_remote_or_synced", lambda _path: False)
    Worker = _worker_type("cancelled", progress=(2, 4), blocking=True)
    monkeypatch.setattr(main_window, "ProtectionWorker", Worker)
    main_thread_id = threading.get_ident()

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(Worker.started.is_set, timeout=1_000)
    qtbot.waitUntil(
        lambda: window._progress_dialog is not None
        and window._progress_dialog.value() == 2,
        timeout=1_000,
    )
    assert window._progress_dialog is not None
    assert window._progress_dialog.maximum() == 4
    assert not window.add_button.isEnabled()
    assert not window.files_view.isEnabled()
    assert not window.password_edit.isEnabled()
    assert not window.printing_checkbox.isEnabled()

    window._progress_dialog.canceled.emit()
    qtbot.waitUntil(lambda: window._thread is None, timeout=1_000)

    processor = Worker.instances[0]
    assert processor.cancel_native_thread == main_thread_id
    assert window.password_edit.text() == ""
    assert window.confirmation_edit.text() == ""
    assert window.add_button.isEnabled()
    assert window.files_view.isEnabled()


@pytest.mark.parametrize("open_folder", [False, True], ids=["stay", "open"])
def test_success_clears_passwords_and_opens_folder_only_after_explicit_choice(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
    tmp_path: Path,
    open_folder: bool,
) -> None:
    """Catches retaining secrets or opening Explorer without explicit consent."""
    source = minimal_pdf_factory("entrada.pdf")
    destination = tmp_path / "resultado.pdf"
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: destination)
    monkeypatch.setattr(main_window, "is_remote_or_synced", lambda _path: False)
    monkeypatch.setattr(
        window, "_ask_open_folder", lambda result: result.destination == destination and open_folder
    )
    opened: list[Path] = []
    monkeypatch.setattr(window, "_open_destination_folder", opened.append)
    Worker = _worker_type("success", progress=(2, 2))
    monkeypatch.setattr(main_window, "ProtectionWorker", Worker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window._thread is None, timeout=1_000)

    assert window.password_edit.text() == ""
    assert window.confirmation_edit.text() == ""
    assert opened == ([destination] if open_folder else [])
    assert window._worker is None
    assert window.add_button.isEnabled()


def test_worker_error_is_reported_and_clears_passwords(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches a silent error, leaked password, or stranded worker thread."""
    source = minimal_pdf_factory("entrada.pdf")
    destination = tmp_path / "resultado.pdf"
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: destination)
    monkeypatch.setattr(main_window, "is_remote_or_synced", lambda _path: False)
    warnings: list[str] = []
    monkeypatch.setattr(
        window, "_show_warning", lambda _title, text: warnings.append(text)
    )
    Worker = _worker_type("failure")
    monkeypatch.setattr(main_window, "ProtectionWorker", Worker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: window._thread is None, timeout=1_000)

    assert warnings == ["No se pudo guardar el PDF protegido."]
    assert PASSWORD not in warnings[0]
    assert window.password_edit.text() == ""
    assert window.confirmation_edit.text() == ""
    assert window._worker is None


def test_close_during_job_cancels_and_waits_for_thread_without_partial_output(
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    minimal_pdf_factory,
    tmp_path: Path,
) -> None:
    """Catches destroying a live QThread or leaving an apparent partial output."""
    source = minimal_pdf_factory("entrada.pdf")
    destination = tmp_path / "resultado.pdf"
    window = _make_window(qtbot)
    _fill_valid_form(window, source)
    monkeypatch.setattr(window, "_choose_destination", lambda: destination)
    monkeypatch.setattr(main_window, "is_remote_or_synced", lambda _path: False)
    Worker = _worker_type("cancelled", blocking=True)
    monkeypatch.setattr(main_window, "ProtectionWorker", Worker)

    qtbot.mouseClick(window.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(Worker.started.is_set, timeout=1_000)
    window.close()
    qtbot.waitUntil(lambda: window._thread is None, timeout=1_000)
    qtbot.waitUntil(lambda: not window.isVisible(), timeout=1_000)

    assert Worker.instances[0].cancel_native_thread is not None
    assert window.password_edit.text() == ""
    assert window.confirmation_edit.text() == ""
    assert not destination.exists()
