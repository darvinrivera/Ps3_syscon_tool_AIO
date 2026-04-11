@echo off
setlocal
cd /d "%~dp0"

echo =====================================================
echo    INSTALADOR DE LIBRERIAS - PS3 SYSCON TOOL
echo =====================================================
echo.

:: 1. Intenta con 'python' (si esta en el PATH)
python --version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Python detectado. Instalando dependencias...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    goto finalizar
)

:: 2. Si falló, intenta con 'py' (el lanzador estandar de Windows)
py --version >nul 2>&1
if %errorlevel% == 0 (
    echo [OK] Python detectado (via lanzador py). Instalando...
    py -m pip install --upgrade pip
    py -m pip install -r requirements.txt
    goto finalizar
)

:: 3. Si nada funciona, avisa al usuario
echo [ERROR] No se encontro Python en este sistema.
echo -----------------------------------------------------
echo Por favor:
echo 1. Descarga Python de https://www.python.org/
echo 2. Al instalar, MARCA la casilla "Add Python to PATH".
echo 3. Reinicia tu PC e intenta de nuevo.
echo.

:finalizar
echo.
echo =====================================================
echo    PROCESO TERMINADO
echo =====================================================
pause
exit