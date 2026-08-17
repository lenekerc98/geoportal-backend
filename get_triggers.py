import psycopg2
conn = psycopg2.connect('postgresql://postgres:L3n3k3rx98.@catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com:5432/catastro-db')
cur = conn.cursor()
cur.execute("SELECT tgname, pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid = 'catastro.predio'::regclass;")
for row in cur.fetchall():
    print(row)
