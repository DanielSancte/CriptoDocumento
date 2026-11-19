"""End-to-end smoke test for the PyInstaller Windows distribution."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

import pikepdf
import pytest
from pikepdf.models.encryption import EncryptionMethod


SMOKE_PASSWORD = "ProtectorPDF-Smoke-Password-Never-Log"
SMOKE_DIRECTORY_ENV = "PDF_PROTECTOR_SMOKE_DIR"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PACKAGED_EXECUTABLE = PROJECT_ROOT / "dist" / "ProtectorPDF" / "ProtectorPDF.exe"


def test_packaged_smoke_loads_qt_and_pikepdf_and_produces_aes256(
    tmp_path: Path,
) -> None:
    """Catches missing Qt/qpdf binaries, weak encryption, or password logging."""
    if not PACKAGED_EXECUTABLE.is_file():
        pytest.skip(
            "Packaged executable is absent; run scripts/build.ps1 before this smoke test."
        )

    smoke_directory = tmp_path / "packaged-smoke"
    environment = os.environ.copy()
    environment[SMOKE_DIRECTORY_ENV] = str(smoke_directory)
    completed = subprocess.run(
        [str(PACKAGED_EXECUTABLE), "--smoke-test"],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=60,
    )
    combined_output = completed.stdout + completed.stderr
    safe_diagnostics = combined_output.replace(SMOKE_PASSWORD, "<redacted>")

    assert completed.returncode == 0, safe_diagnostics
    assert SMOKE_PASSWORD not in combined_output
    assert (PACKAGED_EXECUTABLE.parent / "README.md").is_file()
    assert (PACKAGED_EXECUTABLE.parent / "THIRD_PARTY_LICENSES.md").is_file()

    report_path = smoke_directory / "smoke-report.json"
    report_text = report_path.read_text(encoding="utf-8")
    report = json.loads(report_text)
    assert report["status"] == "ok"
    assert report["qt_version"]
    assert report["qt_application"] == "QApplication"
    assert report["qt_platform"] == "windows"
    assert report["pikepdf_version"]
    assert report["pages"] == 1
    assert report["encryption"] == {"bits": 256, "revision": 6}
    assert SMOKE_PASSWORD not in report_text

    source = smoke_directory / "smoke-source.pdf"
    output = smoke_directory / "smoke-output.pdf"
    with pikepdf.open(source) as unencrypted:
        assert len(unencrypted.pages) == 1
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(output, password="incorrect-smoke-password")
    with pikepdf.open(output, password=SMOKE_PASSWORD) as encrypted:
        assert len(encrypted.pages) == 1
        assert encrypted.encryption.bits == 256
        assert encrypted.encryption.R == 6
        assert encrypted.encryption.file_method is EncryptionMethod.aesv3
        assert encrypted.encryption.stream_method is EncryptionMethod.aesv3
        assert encrypted.encryption.string_method is EncryptionMethod.aesv3
