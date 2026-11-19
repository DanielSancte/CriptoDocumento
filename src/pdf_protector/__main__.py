"""Executable module for ``python -m pdf_protector``."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
from collections.abc import Sequence


SMOKE_PASSWORD = "ProtectorPDF-Smoke-Password-Never-Log"
SMOKE_SOURCE_NAME = "smoke-source.pdf"
SMOKE_OUTPUT_NAME = "smoke-output.pdf"
SMOKE_REPORT_NAME = "smoke-report.json"
SMOKE_DIRECTORY_ENV = "PDF_PROTECTOR_SMOKE_DIR"


def run_smoke_test(directory: Path) -> None:
    """Exercise Qt loading and the real encrypted-output pipeline."""
    import pikepdf
    from pikepdf.models.encryption import EncryptionMethod
    from PySide6.QtCore import qVersion
    from PySide6.QtWidgets import QApplication, QWidget

    from pdf_protector.domain import PdfPermissions, ProtectionRequest
    from pdf_protector.output_service import protect_to_destination

    application = QApplication.instance()
    if application is None:
        application = QApplication(
            ["ProtectorPDF smoke test", "-platform", "windows"]
        )
    if not isinstance(application, QApplication):
        raise RuntimeError("QtWidgets QApplication is unavailable")

    widget_probe = QWidget()
    widget_probe.ensurePolished()
    application.processEvents()
    qt_platform = application.platformName()
    widget_probe.close()
    if qt_platform.casefold() != "windows":
        raise RuntimeError("Qt Windows platform plugin smoke verification failed")

    directory.mkdir(parents=True, exist_ok=True)
    source = directory / SMOKE_SOURCE_NAME
    destination = directory / SMOKE_OUTPUT_NAME

    with pikepdf.Pdf.new() as document:
        document.add_blank_page(page_size=(72, 72))
        document.save(source)

    result = protect_to_destination(
        ProtectionRequest(
            sources=(source,),
            destination=destination,
            user_password=SMOKE_PASSWORD,
            permissions=PdfPermissions(False, False, False),
        )
    )

    with pikepdf.open(destination, password=SMOKE_PASSWORD) as encrypted:
        encryption = encrypted.encryption
        if (
            result.pages != 1
            or len(encrypted.pages) != 1
            or encryption.bits != 256
            or encryption.R != 6
            or encryption.file_method is not EncryptionMethod.aesv3
            or encryption.stream_method is not EncryptionMethod.aesv3
            or encryption.string_method is not EncryptionMethod.aesv3
        ):
            raise RuntimeError("Packaged PDF encryption smoke verification failed")

    report = {
        "status": "ok",
        "qt_version": qVersion(),
        "qt_application": type(application).__name__,
        "qt_platform": qt_platform,
        "pikepdf_version": pikepdf.__version__,
        "pages": result.pages,
        "encryption": {"bits": 256, "revision": 6},
    }
    (directory / SMOKE_REPORT_NAME).write_text(
        json.dumps(report, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_smoke_mode() -> int:
    configured_directory = os.environ.get(SMOKE_DIRECTORY_ENV)
    if configured_directory is None:
        with tempfile.TemporaryDirectory(prefix="protector-pdf-smoke-") as temporary:
            try:
                run_smoke_test(Path(temporary))
            except Exception:
                return 1
        return 0

    directory = Path(configured_directory)
    try:
        run_smoke_test(directory)
    except Exception as error:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            (directory / SMOKE_REPORT_NAME).write_text(
                json.dumps(
                    {"status": "error", "error_type": type(error).__name__},
                    ensure_ascii=True,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the packaged smoke probe or preserve the normal desktop behavior."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--smoke-test"]:
        return _run_smoke_mode()

    from pdf_protector.main_window import main as run_gui

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main())
