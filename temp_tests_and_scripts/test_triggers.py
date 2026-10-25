from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
try:
    with engine.begin() as conn:
        res = conn.execute(text("SELECT tgname, tgfoid::regproc FROM pg_trigger WHERE tgrelid = 'catastro.predio'::regclass"))
        print('Triggers:', res.fetchall())
except Exception as e:
    print('Exception:', str(e))
