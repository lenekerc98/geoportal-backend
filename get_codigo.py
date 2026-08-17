import psycopg2
conn = psycopg2.connect('postgresql://postgres:L3n3k3rx98.@catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com:5432/catastro-db')
cur = conn.cursor()
cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'codigo_catastral' ORDER BY ordinal_position;")
for row in cur.fetchall():
    print(row)
