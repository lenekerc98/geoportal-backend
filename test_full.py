from sqlalchemy import create_engine, text

engine = create_engine('postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db')
geojson_str = '{"type": "Polygon", "coordinates": [[[670298.74, 9840679.39], [670438.27, 9840687.87], [670437.99, 9840682.62], [670441.33, 9840677.08], [670481.71, 9840677.33], [670298.74, 9840679.39]]]}'

try:
    with engine.begin() as db:
        geom_sql = "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 32717)"
        query = text(f'''
            INSERT INTO catastro.predio (posesionario_id, cod_catastral, geom)
            VALUES (2, '010101011', {geom_sql})
            RETURNING id;
        ''')
        result = db.execute(query, {"geojson": geojson_str})
        predio_id = result.scalar()
        print('Inserted predio_id:', predio_id)
        
        query_puntos = text('''
            INSERT INTO catastro.vertice (predio_id, cod_catastral, codigo, coord_x, coord_y, geom)
            SELECT 
                p.id, p.cod_catastral, 
                'P' || LPAD(i::text, 2, '0'),
                ST_X(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i)),
                ST_Y(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i)),
                ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i)
            FROM catastro.predio p
            CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(p.geom, 1))) - 1) as i
            WHERE p.id = :id
        ''')
        db.execute(query_puntos, {"id": predio_id})
        print('Points inserted!')

        query_lineas = text('''
            INSERT INTO catastro.linea_lindero (predio_id, cod_catastral, longitud, rumbo, colindante, geom)
            SELECT 
                p.id, p.cod_catastral,
                ST_Length(ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i+1))),
                NULL,
                '',
                ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i+1))
            FROM catastro.predio p
            CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(p.geom, 1))) - 1) as i
            WHERE p.id = :id
        ''')
        db.execute(query_lineas, {"id": predio_id})
        print('Lines inserted!')
        
        # Rollback anyway for test
        raise Exception('Test complete, rolling back')
except Exception as e:
    print('Exception:', str(e))
