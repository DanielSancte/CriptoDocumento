"""Tests for the non-interactive packaged-application smoke mode."""

from __future__ import annotations

import json
from pathlib import Path

import pikepdf
import pytest
from pikepdf.models.encryption import EncryptionMethod

from pdf_protector import __main__ as app_main


def test_smoke_mode_loads_dependencies_and_creates_verified_aes256_pdf(
    tmp_path: Path,
) -> None:
    """Catches a smoke mode that omits Qt/pikepdf or emits weak/plaintext output."""
    app_main.run_smoke_test(tmp_path)

    source = tmp_path / app_main.SMOKE_SOURCE_NAME
    output = tmp_path / app_main.SMOKE_OUTPUT_NAME
    report_path = tmp_path / app_main.SMOKE_REPORT_NAME
    report_text = report_path.read_text(encoding="utf-8")
    report = json.loads(report_text)

    assert source.is_file()
    assert output.is_file()
    assert report["status"] == "ok"
    assert report["qt_version"]
    assert report["pikepdf_version"] == pikepdf.__version__
    assert report["pages"] == 1
    assert report["encryption"] == {"bits": 256, "revision": 6}
    assert app_main.SMOKE_PASSWORD not in report_text

    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(output, password="incorrect-smoke-password")
    with pikepdf.open(output, password=app_main.SMOKE_PASSWORD) as encrypted:
        assert len(encrypted.pages) == 1
        assert encrypted.encryption.bits == 256
        assert encrypted.encryption.R == 6
        assert encrypted.encryption.file_method is EncryptionMethod.aesv3
        assert encrypted.encryption.stream_method is EncryptionMethod.aesv3
        assert encrypted.encryption.string_method is EncryptionMethod.aesv3


def test_main_dispatches_exact_smoke_flag_without_starting_the_gui(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Catches the packaged entrypoint opening Qt's event loop during smoke."""
    monkeypatch.setenv("PDF_PROTECTOR_SMOKE_DIR", str(tmp_path))

    exit_code = app_main.main(["--smoke-test"])

    assert exit_code == 0
    assert (tmp_path / app_main.SMOKE_OUTPUT_NAME).is_file()
    assert (tmp_path / app_main.SMOKE_REPORT_NAME).is_file()
