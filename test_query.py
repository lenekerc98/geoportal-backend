from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
try:
    with engine.begin() as conn:
        res = conn.execute(text('''
        SELECT 
            '010101011' as cod_catastral, 
            'P' || LPAD(i::text, 2, '0') as codigo,
            ST_X(ST_PointN(ST_ExteriorRing(ST_GeometryN(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'), 1)), i)) as x,
            ST_Y(ST_PointN(ST_ExteriorRing(ST_GeometryN(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'), 1)), i)) as y
        FROM generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'), 1))) - 1) as i
        '''))
        print('Query result:', res.fetchall())
except Exception as e:
    print('Exception:', str(e))
