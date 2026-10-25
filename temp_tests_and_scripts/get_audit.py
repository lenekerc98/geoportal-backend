import psycopg2
conn = psycopg2.connect('postgresql://postgres:L3n3k3rx98.@catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com:5432/catastro-db')
cur = conn.cursor()
cur.execute("SELECT id, nivel, accion, descripcion, usuario_id, fecha FROM seguridad.audit_log WHERE accion = 'PREDIO_CREATED' ORDER BY id DESC LIMIT 5;")
for row in cur.fetchall():
    print(row)
