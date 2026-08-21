from sqlalchemy import create_engine
import json

engine = create_engine('postgresql://postgres:postgres@localhost:5432/catastro_db')
with engine.connect() as conn:
    roles = conn.execute('SELECT * FROM seguridad.rol').fetchall()
    print("Roles in DB:")
    for r in roles:
        print(dict(r))
