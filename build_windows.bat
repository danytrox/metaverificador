@echo off
REM Build para Windows (doble clic). Requiere Python 3.11/3.12 en el PATH.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 (
    echo.
    echo Fallo el build. Revisa el mensaje anterior.
    pause
) else (
    echo.
    echo Ejecutable generado en dist\MetaVerificador.exe
    pause
)
