import os
from osgeo import gdal

gdal.UseExceptions()

source_tif = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Ortofotos\Ortofoto_Completa.tif"
vrt_file = r"C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt"
ovr_file = vrt_file + ".ovr"

print("1. Borrando VRT y OVR antiguos si existen...")
if os.path.exists(vrt_file):
    os.remove(vrt_file)
if os.path.exists(ovr_file):
    os.remove(ovr_file)

print(f"2. Construyendo nuevo VRT desde: {source_tif}")
vrt_options = gdal.BuildVRTOptions(resampleAlg='nearest', addAlpha=True)
vrt_ds = gdal.BuildVRT(vrt_file, [source_tif], options=vrt_options)

if vrt_ds is None:
    print("Error construyendo VRT")
    exit(1)

print("3. Construyendo Overviews (OVR) para el VRT... (ESTO PUEDE TARDAR, POR FAVOR ESPERA)")
gdal.SetConfigOption('COMPRESS_OVERVIEW', 'DEFLATE')
gdal.SetConfigOption('GDAL_NUM_THREADS', 'ALL_CPUS')
vrt_ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64, 128])

# Cerrar el dataset para asegurar que se guarde en disco
vrt_ds = None

print("¡Proceso completado exitosamente! El VRT y OVR están listos.")
