@echo off
echo Iniciando Servidor Catastro 2026 con motor QGIS...

call "C:\Program Files\QGIS 4.0.2\bin\o4w_env.bat"
call "C:\Program Files\QGIS 4.0.2\bin\qt6_env.bat"

path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python;%PYTHONPATH%

echo Entorno GDAL cargado correctamente. Iniciando Uvicorn...
"C:\Program Files\QGIS 4.0.2\apps\Python312\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
