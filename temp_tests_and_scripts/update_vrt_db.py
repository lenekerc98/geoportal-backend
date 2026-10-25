import os
import shutil
import psycopg2
from osgeo import gdal

# Rutas
backend_dir = r"C:\LNCZ\proyecto-catastro-2026\backend"
comp_dir = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos"
db_url = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"

vrt_src = os.path.join(backend_dir, "ortofotos.vrt")
ovr_src = os.path.join(backend_dir, "ortofotos.vrt.ovr")

vrt_dst = os.path.join(comp_dir, "ortofotos.vrt")
ovr_dst = os.path.join(comp_dir, "ortofotos.vrt.ovr")

print("1. Copiando archivos a Complementos...")
if os.path.exists(vrt_src):
    shutil.copy2(vrt_src, vrt_dst)
if os.path.exists(ovr_src):
    shutil.copy2(ovr_src, ovr_dst)

print("2. Obteniendo datos geográficos del nuevo VRT...")
gdal.UseExceptions()
ds = gdal.Open(vrt_dst)
if ds is None:
    print("No se pudo abrir el VRT destino.")
    exit(1)

gt = ds.GetGeoTransform()
cols = ds.RasterXSize
rows = ds.RasterYSize
proj = ds.GetProjection()

minx = gt[0]
miny = gt[3] + cols * gt[4] + rows * gt[5]
maxx = gt[0] + cols * gt[1] + rows * gt[2]
maxy = gt[3]

wkt_geom = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
srid = 32717

ds = None

print("3. Actualizando la base de datos...")
try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM catastro.ortofotos_catalogo WHERE nombre_archivo = 'ortofotos.vrt'")
    
    cursor.execute("""
        INSERT INTO catastro.ortofotos_catalogo 
        (nombre_archivo, ruta_completa, srid, geom, geom_3857, fecha_registro)
        VALUES ('ortofotos.vrt', %s, %s, ST_SetSRID(ST_GeomFromText(%s), %s), ST_Transform(ST_SetSRID(ST_GeomFromText(%s), %s), 3857), CURRENT_TIMESTAMP)
    """, (vrt_dst, srid, wkt_geom, srid, wkt_geom, srid))
    
    conn.commit()
    cursor.close()
    conn.close()
    print("¡Base de datos actualizada con éxito!")
except Exception as e:
    print("Error actualizando la base de datos:", e)
