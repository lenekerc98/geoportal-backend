import psycopg2

db_url = "postgresql://postgres:lenekerc98@127.0.0.1:5432/catastro_db"
vrt_dst = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\ortofotos.vrt"

# Use the exact same values
minx = 667641.0815115151
miny = 9837288.643214187
maxx = 673137.3485115151
maxy = 9844352.272141857
wkt_geom = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"
srid = 32717

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
    print("SUCCESS")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(repr(e))
