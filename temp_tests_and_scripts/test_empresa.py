from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
query = text('''
    SELECT empresa_id, count(*)
    FROM catastro.predio
    GROUP BY empresa_id
''')

res = db.execute(query).fetchall()
print("EMPRESAS IN PREDIOS:", res)
