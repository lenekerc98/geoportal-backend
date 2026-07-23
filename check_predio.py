import psycopg2
db_url = "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db"
conn = psycopg2.connect(db_url)
cursor = conn.cursor()
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'predio'")
print("PREDIO:", [row for row in cursor.fetchall()])
cursor.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'cantones'")
print("CANTONES:", [row for row in cursor.fetchall()])
