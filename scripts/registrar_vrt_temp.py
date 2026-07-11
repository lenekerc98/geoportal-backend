import os
from osgeo import gdal, osr
import psycopg2

VRT_FILE = r"C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt"
DB_URL = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"

print("Calculando polígono gigante del VRT...")
gdal.UseExceptions()
ds = gdal.Open(VRT_FILE)
width = ds.RasterXSize
height = ds.RasterYSize
gt = ds.GetGeoTransform()
        
xmin = gt[0]
ymax = gt[3]
xmax = xmin + width * gt[1] + height * gt[2]
ymin = ymax + width * gt[4] + height * gt[5]

wkt_geom = f"POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))"
ds = None

print("Conectando a PostgreSQL...")
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

try:
    cursor.execute("""
        INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, geom)
        VALUES ('ortofotos.vrt', %s, 32717, ST_Transform(ST_GeomFromText(%s, 32717), 32717))
        ON CONFLICT (nombre_archivo) 
        DO UPDATE SET ruta_completa = EXCLUDED.ruta_completa, geom = EXCLUDED.geom;
    """, (VRT_FILE, wkt_geom))
    conn.commit()
    print("¡VRT Maestro registrado en la base de datos con éxito como referencia central!")
except Exception as e:
    print("Error:", e)
    conn.rollback()
finally:
    cursor.close()
    conn.close()
