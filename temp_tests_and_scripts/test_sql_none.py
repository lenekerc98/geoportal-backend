from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
query = text('''
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'id', id,
                    'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json,
                    'properties', json_build_object(
                        'cod_catastral', cod_catastral,
                        'id', id,
                        'posesionario_id', posesionario_id,
                        'area_ha', area_ha,
                        'cedula', cedula,
                        'nombre_posesionario', nombre_posesionario,
                        'estado', estado,
                        'fecha_creacion', fecha_creacion,
                        'fecha_baja', fecha_baja,
                        'predio_padre_id', predio_padre_id
                    )
                )
            ), '[]'::json)
        )
        FROM catastro.v_predio_completo
        WHERE (CAST(:empresa_id AS INTEGER) IS NULL OR empresa_id = :empresa_id)
        AND fecha_baja IS NULL
''')

try:
    res = db.execute(query, {'empresa_id': None}).scalar_one_or_none()
    print("SUCCESS WITH NONE")
except Exception as e:
    import traceback
    traceback.print_exc()
