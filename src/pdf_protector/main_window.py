"""Accessible single-window workflow for protecting PDF documents."""

from __future__ import annotations

from pathlib import Path
import sys

from PySide6.QtCore import QDir, QProcess, QStandardPaths, QThread, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from pdf_protector.domain import (
    PasswordCompatibilityError,
    PdfPermissions,
    ProcessingResult,
    ProtectionRequest,
)
from pdf_protector.output_service import is_remote_or_synced
from pdf_protector.passwords import validate_password_pair
from pdf_protector.worker import ProtectionWorker


_PATH_ROLE = Qt.ItemDataRole.UserRole


def _resolved_path(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _path_key(path: str | Path) -> str:
    """Return a Windows-style case-insensitive identity for one resolved path."""
    return str(_resolved_path(path)).replace("/", "\\").casefold()


class MainWindow(QMainWindow):
    """The application's complete linear protection workflow."""

    cancellation_requested = Signal()
    signature_decision = Signal(bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: ProtectionWorker | None = None
        self._progress_dialog: QProgressDialog | None = None
        self._pending_outcome: tuple[str, object | None] | None = None
        self._cleanup_warnings: list[str] = []
        self._closing = False

        self.setWindowTitle("Protección de documentos PDF")
        self.setMinimumSize(680, 480)
        self.resize(760, 520)
        self._build_interface()
        self._connect_interface()
        self._update_controls()

    def _build_interface(self) -> None:
        central = QWidget(self)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(16)

        heading = QLabel("Protección de documentos PDF", central)
        heading_font = QFont(heading.font())
        heading_font.setPointSize(15)
        heading_font.setBold(True)
        heading.setFont(heading_font)
        heading.setAccessibleName("Protección de documentos PDF")
        root.addWidget(heading)

        files_group = QGroupBox("Archivos seleccionados", central)
        files_layout = QHBoxLayout(files_group)
        self.files_model = QStandardItemModel(self)
        self.files_view = QListView(files_group)
        self.files_view.setModel(self.files_model)
        self.files_view.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.files_view.setAccessibleName("Lista ordenada de archivos PDF")
        self.files_view.setAccessibleDescription(
            "El orden de esta lista será el orden del documento combinado."
        )
        self.files_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        files_layout.addWidget(self.files_view, 1)

        file_buttons = QVBoxLayout()
        self.add_button = QPushButton("Agregar PDF", files_group)
        self.move_up_button = QPushButton("Subir", files_group)
        self.move_down_button = QPushButton("Bajar", files_group)
        self.remove_button = QPushButton("Quitar", files_group)
        for button, name in (
            (self.add_button, "Agregar archivos PDF"),
            (self.move_up_button, "Subir archivo seleccionado"),
            (self.move_down_button, "Bajar archivo seleccionado"),
            (self.remove_button, "Quitar archivo seleccionado"),
        ):
            button.setAccessibleName(name)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setMinimumWidth(120)
            file_buttons.addWidget(button)
        file_buttons.addStretch(1)
        files_layout.addLayout(file_buttons)
        root.addWidget(files_group, 1)

        credentials_group = QGroupBox("Contraseña de apertura", central)
        credentials_layout = QFormLayout(credentials_group)
        credentials_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        self.password_label = QLabel("Contraseña", credentials_group)
        self.password_edit = QLineEdit(credentials_group)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_edit.setAccessibleName("Contraseña de apertura")
        self.password_edit.setAccessibleDescription(
            "Escriba una contraseña no vacía para abrir el PDF protegido."
        )
        self.password_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.password_label.setBuddy(self.password_edit)

        password_row = QWidget(credentials_group)
        password_row_layout = QHBoxLayout(password_row)
        password_row_layout.setContentsMargins(0, 0, 0, 0)
        self.show_password_button = QToolButton(password_row)
        self.show_password_button.setText("Mostrar")
        self.show_password_button.setCheckable(True)
        self.show_password_button.setAccessibleName("Mostrar contraseñas")
        self.show_password_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        password_row_layout.addWidget(self.password_edit, 1)
        password_row_layout.addWidget(self.show_password_button)
        credentials_layout.addRow(self.password_label, password_row)

        self.confirmation_label = QLabel("Confirmar", credentials_group)
        self.confirmation_edit = QLineEdit(credentials_group)
        self.confirmation_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirmation_edit.setAccessibleName("Confirmar contraseña de apertura")
        self.confirmation_edit.setAccessibleDescription(
            "Repita exactamente la contraseña de apertura."
        )
        self.confirmation_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.confirmation_label.setBuddy(self.confirmation_edit)
        credentials_layout.addRow(self.confirmation_label, self.confirmation_edit)
        root.addWidget(credentials_group)

        permissions_group = QGroupBox("Permisos del documento", central)
        permissions_layout = QHBoxLayout(permissions_group)
        self.printing_checkbox = QCheckBox("Permitir impresión", permissions_group)
        self.copying_checkbox = QCheckBox(
            "Permitir copiar contenido", permissions_group
        )
        self.editing_checkbox = QCheckBox("Permitir edición", permissions_group)
        for checkbox in (
            self.printing_checkbox,
            self.copying_checkbox,
            self.editing_checkbox,
        ):
            checkbox.setChecked(False)
            checkbox.setAccessibleName(checkbox.text())
            checkbox.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            permissions_layout.addWidget(checkbox)
        permissions_layout.addStretch(1)
        root.addWidget(permissions_group)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.create_button = QPushButton("Crear PDF protegido", central)
        self.create_button.setAccessibleName("Crear PDF protegido")
        self.create_button.setAccessibleDescription(
            "Elija el destino e inicie la protección de los archivos seleccionados."
        )
        self.create_button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.create_button.setDefault(True)
        self.create_button.setMinimumWidth(190)
        self.create_button.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        action_row.addWidget(self.create_button)
        root.addLayout(action_row)

        self.setCentralWidget(central)
        self._set_tab_order()

    def _set_tab_order(self) -> None:
        controls = (
            self.add_button,
            self.files_view,
            self.move_up_button,
            self.move_down_button,
            self.remove_button,
            self.password_edit,
            self.confirmation_edit,
            self.show_password_button,
            self.printing_checkbox,
            self.copying_checkbox,
            self.editing_checkbox,
            self.create_button,
        )
        for first, second in zip(controls, controls[1:]):
            QWidget.setTabOrder(first, second)

    def _connect_interface(self) -> None:
        self.add_button.clicked.connect(self._select_sources)
        self.move_up_button.clicked.connect(lambda: self._move_selected(-1))
        self.move_down_button.clicked.connect(lambda: self._move_selected(1))
        self.remove_button.clicked.connect(self._remove_selected)
        self.show_password_button.toggled.connect(self._toggle_passwords)
        self.password_edit.textChanged.connect(self._update_controls)
        self.confirmation_edit.textChanged.connect(self._update_controls)
        self.files_model.rowsInserted.connect(self._update_controls)
        self.files_model.rowsRemoved.connect(self._update_controls)
        self.files_model.rowsMoved.connect(self._update_controls)
        self.files_view.selectionModel().currentChanged.connect(
            self._update_selection_controls
        )
        self.create_button.clicked.connect(self._create_protected_pdf)

    def source_paths(self) -> tuple[Path, ...]:
        """Return the ordered full source paths retained by the model."""
        return tuple(
            Path(self.files_model.item(row).data(_PATH_ROLE))
            for row in range(self.files_model.rowCount())
        )

    def add_sources(self, paths: list[str | Path] | tuple[Path, ...]) -> None:
        """Add supported unique paths in caller-provided order."""
        existing = {_path_key(path) for path in self.source_paths()}
        duplicates: list[str] = []
        invalid: list[str] = []

        for raw_path in paths:
            path = _resolved_path(raw_path)
            if path.suffix.casefold() != ".pdf":
                invalid.append(path.name)
                continue
            key = _path_key(path)
            if key in existing:
                duplicates.append(path.name)
                continue
            existing.add(key)
            item = QStandardItem(path.name)
            item.setEditable(False)
            item.setData(str(path), _PATH_ROLE)
            item.setAccessibleText(path.name)
            self.files_model.appendRow(item)

        if self.files_model.rowCount() and not self.files_view.currentIndex().isValid():
            self.files_view.setCurrentIndex(self.files_model.index(0, 0))
        if invalid:
            self._show_information(
                "Archivos no admitidos",
                "Solo se pueden agregar archivos PDF. No se agregaron: "
                + ", ".join(invalid),
            )
        if duplicates:
            self._show_information(
                "Archivos ya seleccionados",
                "Estos archivos ya estaban seleccionados y no se agregaron otra vez: "
                + ", ".join(duplicates),
            )
        self._update_controls()

    @Slot()
    def _select_sources(self) -> None:
        paths, _selected_filter = QFileDialog.getOpenFileNames(
            self,
            "Seleccionar archivos PDF",
            str(Path.home()),
            "Archivos PDF (*.pdf)",
        )
        if paths:
            self.add_sources(paths)

    def _selected_row(self) -> int:
        index = self.files_view.currentIndex()
        return index.row() if index.isValid() else -1

    def _move_selected(self, delta: int) -> None:
        row = self._selected_row()
        target = row + delta
        if row < 0 or target < 0 or target >= self.files_model.rowCount():
            return
        items = self.files_model.takeRow(row)
        self.files_model.insertRow(target, items)
        self.files_view.setCurrentIndex(self.files_model.index(target, 0))
        self._update_controls()

    @Slot()
    def _remove_selected(self) -> None:
        row = self._selected_row()
        if row < 0:
            return
        self.files_model.removeRow(row)
        remaining = self.files_model.rowCount()
        if remaining:
            self.files_view.setCurrentIndex(
                self.files_model.index(min(row, remaining - 1), 0)
            )
        self._update_controls()

    @Slot(bool)
    def _toggle_passwords(self, shown: bool) -> None:
        mode = QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
        self.password_edit.setEchoMode(mode)
        self.confirmation_edit.setEchoMode(mode)
        self.show_password_button.setText("Ocultar" if shown else "Mostrar")
        self.show_password_button.setAccessibleName(
            "Ocultar contraseñas" if shown else "Mostrar contraseñas"
        )

    def _form_is_valid(self) -> bool:
        if self.files_model.rowCount() == 0:
            return False
        try:
            validate_password_pair(
                self.password_edit.text(), self.confirmation_edit.text()
            )
        except PasswordCompatibilityError:
            return False
        return True

    def _scrub_password_fields(self) -> None:
        """Erase password text and QLineEdit's undo/redo history."""
        self.password_edit.setText("")
        self.confirmation_edit.setText("")
        self.show_password_button.setChecked(False)

    def _abort_with_warning(self, title: str, text: str) -> None:
        self._scrub_password_fields()
        self._show_warning(title, text)

    @Slot()
    def _update_controls(self) -> None:
        processing = self._thread is not None
        for control in (
            self.add_button,
            self.files_view,
            self.password_edit,
            self.confirmation_edit,
            self.show_password_button,
            self.printing_checkbox,
            self.copying_checkbox,
            self.editing_checkbox,
        ):
            control.setEnabled(not processing)
        self.create_button.setEnabled(not processing and self._form_is_valid())
        self._update_selection_controls()

    @Slot()
    def _update_selection_controls(self, *_args: object) -> None:
        processing = self._thread is not None
        row = self._selected_row()
        count = self.files_model.rowCount()
        self.move_up_button.setEnabled(not processing and row > 0)
        self.move_down_button.setEnabled(
            not processing and row >= 0 and row < count - 1
        )
        self.remove_button.setEnabled(not processing and row >= 0)

    def default_destination(self) -> Path:
        """Return the native Documents location with the approved default name."""
        documents = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        parent = _resolved_path(documents) if documents else Path.home().resolve()
        return parent / "documentos_protegidos.pdf"

    def _choose_destination(self) -> Path | None:
        selected, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Guardar PDF protegido",
            str(self.default_destination()),
            "Archivos PDF (*.pdf)",
            options=QFileDialog.Option.DontConfirmOverwrite,
        )
        if not selected:
            return None
        destination = _resolved_path(selected)
        if destination.suffix.casefold() != ".pdf":
            destination = destination.with_name(destination.name + ".pdf")
        return destination

    @Slot()
    def _create_protected_pdf(self) -> None:
        if self._thread is not None:
            return
        try:
            validate_password_pair(
                self.password_edit.text(), self.confirmation_edit.text()
            )
        except PasswordCompatibilityError as error:
            self._abort_with_warning("Contraseña no válida", str(error))
            return

        sources = self.source_paths()
        if not sources:
            self._abort_with_warning(
                "Sin archivos", "Debe seleccionar al menos un archivo PDF."
            )
            return

        missing_source = next((path for path in sources if not path.is_file()), None)
        if missing_source is not None:
            self._abort_with_warning(
                "No se puede usar el archivo",
                f"No se pudo abrir el PDF de origen '{missing_source.name}'.",
            )
            return

        destination = self._choose_destination()
        if destination is None:
            self._scrub_password_fields()
            return
        if _path_key(destination) in {_path_key(path) for path in sources}:
            self._abort_with_warning(
                "Destino no válido",
                "El destino no puede reemplazar un archivo original seleccionado.",
            )
            return

        if is_remote_or_synced(destination.parent) and not self._confirm(
            "Ubicación de red o sincronizada",
            "La carpeta elegida parece ser de red o estar sincronizada. "
            "El servicio correspondiente podría transmitir el resultado. "
            "¿Desea continuar?",
        ):
            self._scrub_password_fields()
            return

        overwrite_confirmed = destination.exists()
        if overwrite_confirmed and not self._confirm(
            "Reemplazar archivo",
            f'El archivo "{destination.name}" ya existe. ¿Desea reemplazarlo?',
        ):
            self._scrub_password_fields()
            return

        request = ProtectionRequest(
            sources=sources,
            destination=destination,
            user_password=self.password_edit.text(),
            permissions=PdfPermissions(
                printing=self.printing_checkbox.isChecked(),
                copying=self.copying_checkbox.isChecked(),
                editing=self.editing_checkbox.isChecked(),
            ),
        )
        self._start_worker(request, overwrite_confirmed=overwrite_confirmed)

    def _start_worker(
        self, request: ProtectionRequest, *, overwrite_confirmed: bool
    ) -> None:
        self._pending_outcome = None
        self._cleanup_warnings = []
        thread = QThread(self)
        worker = ProtectionWorker(
            request, overwrite_confirmed=overwrite_confirmed
        )
        worker.moveToThread(thread)
        self._thread = thread
        self._worker = worker

        progress = QProgressDialog(
            "Preparando los documentos PDF…", "Cancelar", 0, 0, self
        )
        progress.setWindowTitle("Creando PDF protegido")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.setAccessibleName("Progreso de protección de PDF")
        progress.canceled.connect(self._request_cancellation)
        self._progress_dialog = progress

        thread.started.connect(worker.run)
        worker.progress.connect(self._update_progress)
        worker.succeeded.connect(self._record_success)
        worker.failed.connect(self._record_failure)
        worker.cancelled.connect(self._record_cancellation)
        worker.warning.connect(self._record_warning)
        worker.signature_confirmation_required.connect(
            self._confirm_signature_invalidation
        )
        worker.succeeded.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        worker.cancelled.connect(worker.deleteLater)
        self.cancellation_requested.connect(
            worker.cancel, Qt.ConnectionType.DirectConnection
        )
        self.signature_decision.connect(
            worker.resolve_signature_confirmation,
            Qt.ConnectionType.DirectConnection,
        )
        thread.finished.connect(self._thread_finished)
        thread.finished.connect(thread.deleteLater)

        self._scrub_password_fields()
        self._update_controls()
        progress.show()
        thread.start()

    @Slot(int, int)
    def _update_progress(self, completed: int, total: int) -> None:
        progress = self._progress_dialog
        if progress is None:
            return
        if total > 0:
            progress.setRange(0, total)
            progress.setValue(min(completed, total))
            progress.setLabelText(
                f"Procesando página {min(completed, total)} de {total}…"
            )

    @Slot(ProcessingResult)
    def _record_success(self, result: ProcessingResult) -> None:
        self._pending_outcome = ("success", result)
        self._stop_thread()

    @Slot(str)
    def _record_failure(self, message: str) -> None:
        self._pending_outcome = ("failure", message)
        self._stop_thread()

    @Slot()
    def _record_cancellation(self) -> None:
        self._pending_outcome = ("cancelled", None)
        self._stop_thread()

    @Slot(str)
    def _record_warning(self, message: str) -> None:
        self._cleanup_warnings.append(message)

    @Slot(object)
    def _confirm_signature_invalidation(self, names: object) -> None:
        signed_names = (
            tuple(str(name) for name in names) if isinstance(names, tuple) else ()
        )
        accepted = self._confirm(
            "Firmas digitales detectadas",
            "Las firmas digitales dejarán de ser válidas al crear el nuevo PDF. "
            "Archivos: "
            + ", ".join(signed_names)
            + ". ¿Desea continuar?",
        )
        if not accepted and self._progress_dialog is not None:
            self._progress_dialog.setLabelText("Cancelando…")
        self.signature_decision.emit(accepted)

    def _stop_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()

    @Slot()
    def _request_cancellation(self) -> None:
        if self._worker is None:
            return
        if self._progress_dialog is not None:
            self._progress_dialog.setLabelText("Cancelando…")
        self.cancellation_requested.emit()

    @Slot()
    def _thread_finished(self) -> None:
        outcome = self._pending_outcome
        cleanup_warnings = tuple(self._cleanup_warnings)
        progress = self._progress_dialog
        if progress is not None:
            progress.hide()
            progress.deleteLater()
        self._progress_dialog = None
        self._worker = None
        self._thread = None
        self._pending_outcome = None
        self._cleanup_warnings = []
        self._scrub_password_fields()
        self._update_controls()

        if self._closing:
            QTimer.singleShot(0, self.close)
            return
        if outcome is None:
            return
        kind, value = outcome
        if kind == "success" and isinstance(value, ProcessingResult):
            if cleanup_warnings:
                self._show_warning(
                    "Limpieza incompleta", "\n".join(cleanup_warnings)
                )
            if self._ask_open_folder(value):
                self._open_destination_folder(value.destination)
        elif kind == "failure" and isinstance(value, str):
            message = value
            if cleanup_warnings:
                message += "\n\nAdvertencia: " + " ".join(cleanup_warnings)
            self._show_warning("No se pudo crear el PDF", message)
        elif kind == "cancelled" and cleanup_warnings:
            self._show_warning("Limpieza incompleta", "\n".join(cleanup_warnings))

    def _show_information(self, title: str, text: str) -> None:
        QMessageBox.information(self, title, text)

    def _show_warning(self, title: str, text: str) -> None:
        QMessageBox.warning(self, title, text)

    def _confirm(self, title: str, text: str) -> bool:
        result = QMessageBox.question(
            self,
            title,
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _ask_open_folder(self, result: ProcessingResult) -> bool:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Information)
        dialog.setWindowTitle("PDF protegido creado")
        dialog.setText(
            "El PDF protegido se creó correctamente.\n\n"
            f"Destino: {result.destination}"
        )
        open_button = dialog.addButton(
            "Abrir carpeta", QMessageBox.ButtonRole.ActionRole
        )
        dialog.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        dialog.exec()
        return dialog.clickedButton() is open_button

    def _open_destination_folder(self, destination: Path) -> None:
        if sys.platform == "win32":
            QProcess.startDetached(
                "explorer.exe",
                ["/select,", QDir.toNativeSeparators(str(destination))],
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(destination.parent)))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        if self._thread is not None:
            self._closing = True
            self._request_cancellation()
            event.ignore()
            return
        event.accept()


def main() -> int:
    """Start the desktop application and return Qt's process exit code."""
    application = QApplication.instance()
    if application is None:
        application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return application.exec()
