import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

try:
    with engine.connect() as db:
        # 1. Predio
        q_predio = text("""
            SELECT id, cod_catastral, area_ha, posesionario_id, nombre_posesionario, cedula, estado, fecha_creacion, fecha_baja, predio_padre_id, ST_AsText(geom) as geom_wkt
            FROM catastro.v_predio_completo 
            WHERE cod_catastral = '0101010112'
        """)
        predio_row = db.execute(q_predio).mappings().first()
        
        if predio_row:
            area_ha = float(predio_row["area_ha"]) if predio_row["area_ha"] is not None else 0.0
            
            # 2. Vértices
            q_vertices = text("""
                SELECT id, predio_id, cod_catastral, codigo, coord_x, coord_y, ST_AsText(geom) as geom_wkt
                FROM catastro.vertice 
                WHERE predio_id = :predio_id
                ORDER BY codigo
            """)
            vertices_rows = db.execute(q_vertices, {"predio_id": predio_row["id"]}).mappings().all()
            for v in vertices_rows:
                cx = float(v["coord_x"]) if v["coord_x"] is not None else 0.0
                cy = float(v["coord_y"]) if v["coord_y"] is not None else 0.0

            # 3. Linderos
            q_linderos = text("""
                SELECT id, predio_id, cod_catastral, longitud, rumbo, colindante, ST_AsText(geom) as geom_wkt
                FROM catastro.linea_lindero 
                WHERE predio_id = :predio_id
                ORDER BY id
            """)
            linderos_rows = db.execute(q_linderos, {"predio_id": predio_row["id"]}).mappings().all()
            for l in linderos_rows:
                longitud = float(l["longitud"]) if l["longitud"] is not None else 0.0

            print("No error tracing floats!")
except Exception as e:
    import traceback
    traceback.print_exc()
