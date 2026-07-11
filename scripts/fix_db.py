import psycopg2

DB_URL = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

ruta_correcta = r"C:\LNCZ\proyecto-catastro-2026\backend\ortofotos.vrt"

cursor.execute("UPDATE catastro.ortofotos_catalogo SET ruta_completa = %s WHERE nombre_archivo = 'ortofotos.vrt'", (ruta_correcta,))

if cursor.rowcount == 0:
    cursor.execute("INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa) VALUES ('ortofotos.vrt', %s)", (ruta_correcta,))

conn.commit()
print("Base de datos actualizada con la ruta correcta del VRT.")
cursor.close()
conn.close()
