import psycopg2

db_url = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"
conn = psycopg2.connect(db_url)
cursor = conn.cursor()
cursor.execute("SELECT nombre_archivo, ruta_completa, tipo_archivo FROM catastro.ortofotos_catalogo")
print(cursor.fetchall())
