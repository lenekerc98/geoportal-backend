
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
with engine.connect() as conn:
    res = conn.execute(text('''
    SELECT conname, pg_get_constraintdef(c.oid)
    FROM pg_constraint c
    JOIN pg_namespace n ON n.oid = c.connamespace
    WHERE n.nspname = 'catastro' AND c.conrelid::regclass::text IN ('catastro.predio', 'catastro.vertice');
    '''))
    for r in res: print(r)

