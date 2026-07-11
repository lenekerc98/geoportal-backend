import psycopg2

DB_URL = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"
conn = psycopg2.connect(DB_URL)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE catastro.ortofotos_catalogo ADD COLUMN IF NOT EXISTS tipo_archivo VARCHAR(10);")
    cursor.execute("UPDATE catastro.ortofotos_catalogo SET tipo_archivo = 'vrt' WHERE nombre_archivo ILIKE '%.vrt';")
    cursor.execute("UPDATE catastro.ortofotos_catalogo SET tipo_archivo = 'tif' WHERE nombre_archivo ILIKE '%.tif' OR nombre_archivo ILIKE '%.tiff';")
    cursor.execute("UPDATE catastro.ortofotos_catalogo SET tipo_archivo = 'ecw' WHERE nombre_archivo ILIKE '%.ecw';")
    conn.commit()
    print("Columna 'tipo_archivo' agregada y actualizada correctamente.")
except Exception as e:
    print(f"Error actualizando DB: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
