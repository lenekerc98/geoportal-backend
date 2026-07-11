@echo off
call "C:\Program Files\QGIS 4.0.2\bin\o4w_env.bat"
call "C:\Program Files\QGIS 4.0.2\bin\qt6_env.bat"
path %OSGEO4W_ROOT%\apps\qgis\bin;%PATH%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\qgis\python;%PYTHONPATH%
"C:\Program Files\QGIS 4.0.2\apps\Python312\python.exe" test_png.py
