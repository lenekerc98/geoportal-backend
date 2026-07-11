import os
from osgeo import gdal

DIR_ORTOFOTOS = r"D:\_Ortofotos\NuevaVentanas"
DIR_DESTINO = r"D:\Ortofotos_unificado"
OUTPUT_TIFF = os.path.join(DIR_DESTINO, "Ortofoto_Completa.tif")

# Crear carpeta destino si no existe
if not os.path.exists(DIR_DESTINO):
    os.makedirs(DIR_DESTINO)

archivos = [f for f in os.listdir(DIR_ORTOFOTOS) if f.lower().endswith(('.tif', '.tiff', '.ecw', '.jp2'))]
rutas_completas = [os.path.join(DIR_ORTOFOTOS, f) for f in archivos]

print(f"Iniciando fusión física de {len(archivos)} ortofotos...")
print(f"Destino: {OUTPUT_TIFF}")
print("Este proceso tomará bastante tiempo. Por favor, no cierres la ventana.")

gdal.UseExceptions()

# Configuraciones optimizadas para ortofotos fotográficas gigantes
creation_options = [
    "BIGTIFF=YES", 
    "TILED=YES", 
    "COMPRESS=LZW",       # Compresión sin pérdida compatible con Alpha
    "PREDICTOR=2",        # Mejora la eficiencia de LZW
    "BLOCKXSIZE=512",
    "BLOCKYSIZE=512"
]

warp_options = gdal.WarpOptions(
    format="GTiff",
    creationOptions=creation_options,
    srcNodata="255 255 255", # Vuelve transparente el fondo blanco original
    dstAlpha=True,           # Crea un canal transparente real en el archivo final
    multithread=True,        # Usa todos los núcleos del procesador para mayor velocidad
    callback=gdal.TermProgress_nocb
)

print("\n--- Paso 1: Unificando imágenes (Warp) ---")
# gdal.Warp fusiona todo en un solo GeoTIFF gigante
gdal.Warp(OUTPUT_TIFF, rutas_completas, options=warp_options)

print("\n--- Paso 2: Construyendo pirámides internas para velocidad extrema ---")
# Abrimos el archivo recién creado para inyectarle las pirámides adentro
ds = gdal.Open(OUTPUT_TIFF, gdal.GA_Update)
ds.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64], callback=gdal.TermProgress_nocb)
ds = None

print(f"\n¡Fusión completada con éxito! Archivo final 100% listo en: {OUTPUT_TIFF}")
