# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir definition for the Windows desktop application."""

from importlib.util import find_spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_all


project_root = Path(SPECPATH).resolve().parent
source_root = project_root / "src"
unwanted_packaged_path_tokens = (
    "/qt6virtualkeyboard",
    "/qtvirtualkeyboard",
    "/qt6pdf",
    "/qtpdf",
    "/qpdf.dll",
    "/pdfium",
    "/qt6webengine",
    "/qtwebengine",
    "/chromium",
    "/opengl32sw.dll",
    "/mesa",
    "/qt6qml",
    "/qt6quick",
    "/qt6opengl",
    "/qml/",
    "/rng2schtrn.xsl",
    "/xsd2schtrn.xsl",
)


def without_unused_payload(entries):
    """Keep optional stacks that the QWidget application uses out of the bundle."""
    return [
        entry
        for entry in entries
        if not any(
            token in ("/" + entry[0].replace("\\", "/").casefold())
            for token in unwanted_packaged_path_tokens
        )
    ]

pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = collect_all(
    "pikepdf",
    filter_submodules=lambda name: not name.startswith("pikepdf.pdfa"),
)
pikepdf_module = find_spec("pikepdf")
if pikepdf_module is None or pikepdf_module.origin is None:
    raise RuntimeError("pikepdf is required to build ProtectorPDF")

# pikepdf wheels built with delvewheel place qpdf and its C++ runtime in a
# sibling directory. Keep that layout so the extension can resolve the DLLs.
pikepdf_libs = Path(pikepdf_module.origin).resolve().parent.parent / "pikepdf.libs"
if not pikepdf_libs.is_dir():
    raise RuntimeError(f"pikepdf native library directory is missing: {pikepdf_libs}")
for library in sorted(pikepdf_libs.glob("*.dll")):
    pikepdf_binaries.append((str(library), "pikepdf.libs"))

analysis = Analysis(
    [str(source_root / "pdf_protector" / "__main__.py")],
    pathex=[str(source_root)],
    binaries=pikepdf_binaries,
    datas=pikepdf_datas,
    hiddenimports=[
        *pikepdf_hiddenimports,
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyInstaller",
        "pytest",
        "pytestqt",
        "setuptools",
        "pip",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "PySide6.QtOpenGL",
        "PySide6.QtOpenGLWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtVirtualKeyboard",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineQuick",
        "PySide6.QtWebEngineWidgets",
    ],
    noarchive=False,
    optimize=0,
)

analysis.binaries = without_unused_payload(analysis.binaries)
analysis.datas = without_unused_payload(analysis.datas)

python_archive = PYZ(analysis.pure)

executable = EXE(
    python_archive,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="ProtectorPDF",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
)

distribution = COLLECT(
    executable,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="ProtectorPDF",
)
