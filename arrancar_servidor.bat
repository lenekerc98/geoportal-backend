@echo off
title Servidor Backend - Catastro 2026
echo ======================================================================
echo          INICIANDO SERVIDOR CATASTRO 2026 CON MOTOR QGIS
echo ======================================================================

set "PYTHON_EXE=C:\Program Files\QGIS 4.0.2\apps\Python312\python.exe"

if not exist "%PYTHON_EXE%" (
    echo [ERROR] No se encontro Python en la ruta: %PYTHON_EXE%
    echo Por favor verifica la instalacion de QGIS 4.0.2.
    pause
    exit /b 1
)

echo [1/3] Cargando entorno GDAL / OGR / QGIS...
call "C:\Program Files\QGIS 4.0.2\bin\o4w_env.bat" >nul 2>&1
call "C:\Program Files\QGIS 4.0.2\bin\qt6_env.bat" >nul 2>&1

path %OSGEO4W_ROOT%\apps\qgis\bin;C:\Program Files\QGIS 4.0.2\apps\Python312;C:\Program Files\QGIS 4.0.2\apps\Python312\Scripts;%PATH%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python;%PYTHONPATH%

echo [2/3] Verificando dependencias de Python (requirements.txt)...
echo       (Si falta alguna libreria se descargara automaticamente)...
"%PYTHON_EXE%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [AVISO] Ocurrio un aviso al verificar paquetes. Continuando...
) else (
    echo [OK] Todas las dependencias estan listas.
)

REM Si el usuario envio argumentos por linea de comandos (ej: arrancar_servidor.bat uvicorn ...):
if not "%~1"=="" (
    echo.
    echo [INFO] Ejecutando comando personalizado: %*
    "%PYTHON_EXE%" -m %*
    goto fin
)

echo.
echo [3/3] Iniciando Uvicorn en http://localhost:8000 (0.0.0.0:8000)...
echo       Presiona Ctrl + C para detener el servidor.
echo ======================================================================
echo.
"%PYTHON_EXE%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

:fin
pause
