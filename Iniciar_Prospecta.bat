@echo off
chcp 65001 >nul
title Prospecta AI - Sistema de Prospeccion B2B
color 0B

echo =========================================================
echo       PROSPECTA AI - AUTOMATIZACION DE VENTAS B2B
echo =========================================================
echo.
echo Iniciando el servidor y preparando la aplicacion...
echo Por favor espera un momento. Se abrira tu navegador web...
echo.

:: Comprobar si Python está instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    color 0C
    echo [ERROR] No se ha encontrado Python en este equipo.
    echo Por favor instala Python 3.10 o superior marcando la casilla
    echo "Add Python to PATH" durante la instalacion.
    echo.
    echo Descargalo en: https://www.python.org/downloads/
    pause
    exit /b
)

:: Si existe un entorno virtual en la carpeta, activarlo
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Iniciar Streamlit y abrir navegador
python -m streamlit run main.py --browser.serverAddress="localhost" --server.port=8501 --server.headless=false

if %errorlevel% neq 0 (
    echo.
    echo Hubo un problema al iniciar la aplicacion.
    echo Si es la primera vez que la ejecutas, instala las librerias con:
    echo    pip install -r requirements.txt
    echo.
    pause
)
