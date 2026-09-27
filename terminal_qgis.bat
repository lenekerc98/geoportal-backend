@echo off
title Consola QGIS / Python 3.12 - Catastro 2026
echo ======================================================================
echo    CONSOLA PRECONFIGURADA CON MOTOR QGIS (GDAL, OGR, PYTHON 3.12)
echo ======================================================================
call "C:\Program Files\QGIS 4.0.2\bin\o4w_env.bat" >nul 2>&1
call "C:\Program Files\QGIS 4.0.2\bin\qt6_env.bat" >nul 2>&1

path %OSGEO4W_ROOT%\apps\qgis\bin;C:\Program Files\QGIS 4.0.2\apps\Python312;C:\Program Files\QGIS 4.0.2\apps\Python312\Scripts;%PATH%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python;%PYTHONPATH%

echo.
echo Entorno listo. Puedes ejecutar directamente cualquiera de estos comandos:
echo   - uvicorn app.main:app --reload --port 8000
echo   - pip install -r requirements.txt
echo   - pip install <nombre-libreria>
echo   - python <script.py>
echo ======================================================================
echo.
cmd /k
