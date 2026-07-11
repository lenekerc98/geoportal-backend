import psycopg2
db_url = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"
conn = psycopg2.connect(db_url)
cursor = conn.cursor()
cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'ortofotos_catalogo'")
print([row[0] for row in cursor.fetchall()])
