# Build para Windows (PowerShell). Genera dist/MetaVerificador.exe
# Requisito: Python 3.11 o 3.12 instalado y en el PATH.

$ErrorActionPreference = "Stop"

Write-Host "== Creando entorno virtual =="
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip

Write-Host "== Instalando dependencias =="
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-build.txt

Write-Host "== Descargando ExifTool =="
& .\.venv\Scripts\python.exe scripts\download_exiftool.py

Write-Host "== Empaquetando con PyInstaller =="
& .\.venv\Scripts\pyinstaller.exe metaverificador.spec --clean --noconfirm

Write-Host ""
Write-Host "Listo. Ejecutable en: dist\MetaVerificador.exe"
