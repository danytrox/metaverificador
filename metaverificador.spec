# -*- mode: python ; coding: utf-8 -*-
# Spec de PyInstaller para empaquetar MetaVerificador como .exe único.
# Ejecutar en Windows:  pyinstaller metaverificador.spec --clean --noconfirm
#
# La IA local (llama-cpp-python) es OPCIONAL. Si está instalada en el entorno
# de build, se empaqueta dentro del .exe (la librería nativa y sus datos). El
# modelo GGUF NO se incluye: se descarga en primer uso con
# `scripts/download_model.py`. Si llama_cpp no está instalado, el .exe se
# genera igualmente, sin la capa de IA (solo mapeo determinístico).

from PyInstaller.utils.hooks import collect_dynamic_libs

datas = [('resources/exiftool', 'exiftool'), ('resources/kofi.png', '.')]
binaries = []
hiddenimports = []

# --- IA local (opcional) ----------------------------------------------------
# llama-cpp-python carga su librería nativa (llama.dll, ggml.dll, …) por ctypes
# desde ``llama_cpp/lib``. Solo recolectamos las DLL y los módulos clave; no se
# usa collect_all() para no arrastrar el servidor opcional (FastAPI/uvicorn).
try:
    import llama_cpp  # noqa: F401
except Exception:
    llama_cpp = None

if llama_cpp is not None:
    try:
        binaries += collect_dynamic_libs('llama_cpp')
    except Exception:
        pass
    hiddenimports += [
        'llama_cpp',
        'llama_cpp._internals',
        'llama_cpp.llama_cpp',
        'llama_cpp._ctypes_extensions',
    ]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtPdf',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MetaVerificador',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
