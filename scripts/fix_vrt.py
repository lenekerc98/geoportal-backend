import os
from osgeo import gdal

DIR_ORTOFOTOS = r"D:\_Ortofotos\NuevaVentanas"
VRT_FILE = r"C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt"

archivos = [f for f in os.listdir(DIR_ORTOFOTOS) if f.lower().endswith(('.tif', '.tiff', '.ecw', '.jp2'))]
rutas_completas = [os.path.join(DIR_ORTOFOTOS, f) for f in archivos]

print("Regenerando VRT con corrección de bordes blancos (Transparencia de 3 canales)...")
gdal.UseExceptions()

# Ahora le decimos "255 255 255" para que solo oculte los píxeles que son BLANCO PURO
# en las 3 bandas (Rojo, Verde, Azul). Así evitamos que borre toda la imagen.
vrt_options = gdal.BuildVRTOptions(
    resampleAlg='near', 
    addAlpha=True, 
    srcNodata="255 255 255", 
    VRTNodata="255 255 255"
)
vrt_ds = gdal.BuildVRT(VRT_FILE, rutas_completas, options=vrt_options)
vrt_ds = None
print("VRT regenerado al instante con transparencia.")
