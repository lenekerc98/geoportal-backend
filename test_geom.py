from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
try:
    with engine.begin() as conn:
        res = conn.execute(text("SELECT ST_AsText(ST_ExteriorRing(ST_GeometryN(ST_GeomFromText('POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))'), 1)))"))
        print('GeometryN Polygon result:', res.scalar())
        res2 = conn.execute(text("SELECT ST_AsText(ST_ExteriorRing(ST_GeometryN(ST_GeomFromText('MULTIPOLYGON(((0 0, 1 0, 1 1, 0 1, 0 0)))'), 1)))"))
        print('GeometryN MultiPolygon result:', res2.scalar())
except Exception as e:
    print('Exception:', str(e))
