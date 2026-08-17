@echo off
title Compilar Piano Autoplayer
cd /d "%~dp0"

echo ============================================
echo   Compilando Piano Autoplayer a .exe
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No encuentro Python.
    echo Instalalo desde python.org y marca "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [1/3] Instalando PyInstaller...
python -m pip install --upgrade pip --quiet
python -m pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de PyInstaller.
    pause
    exit /b 1
)

echo [2/3] Compilando (tarda 1-2 minutos)...
python -m PyInstaller --onefile --noconsole --clean ^
    --name "PianoAutoplayer" --distpath ..\packages ^
    ..\src\autoplayer.py

if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion.
    pause
    exit /b 1
)

echo [3/3] Limpiando archivos temporales...
rmdir /s /q build 2>nul
del PianoAutoplayer.spec 2>nul

echo.
echo ============================================
echo   LISTO
echo   El ejecutable esta en:  packages\PianoAutoplayer.exe
echo   Podes moverlo a donde quieras, es autonomo.
echo ============================================
echo.
pause
