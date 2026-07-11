from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
try:
    with engine.begin() as conn:
        res = conn.execute(text("SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'catastro' AND table_name = 'codigo_catastral'"))
        print('codigo_catastral cols:', res.fetchall())
except Exception as e:
    print('Exception:', str(e))
