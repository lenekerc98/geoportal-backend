import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

import sys
sys.path.append("C:/LNCZ/proyecto-catastro-2026/backend")

from app.schemas.gis import PredioDetalleEspacial, Predio, Vertice, Lindero

load_dotenv()
engine = create_engine(os.getenv("DATABASE_URL"))

try:
    with engine.connect() as db:
        q_predio = text("""
            SELECT id, cod_catastral, area_ha, posesionario_id, nombre_posesionario, cedula, estado, fecha_creacion, fecha_baja, predio_padre_id, ST_AsText(geom) as geom_wkt
            FROM catastro.v_predio_completo 
            WHERE cod_catastral = '0101010112'
        """)
        predio_row = db.execute(q_predio).mappings().first()
        
        predio_data = Predio(
            id=predio_row["id"],
            cod_catastral=predio_row["cod_catastral"],
            area_ha=float(predio_row["area_ha"]),
            posesionario_id=predio_row["posesionario_id"],
            nombre_posesionario=predio_row["nombre_posesionario"],
            cedula=predio_row["cedula"],
            geom_wkt=predio_row["geom_wkt"]
        )
        
        q_vertices = text("""
            SELECT id, predio_id, cod_catastral, codigo, coord_x, coord_y, ST_AsText(geom) as geom_wkt
            FROM catastro.vertice 
            WHERE predio_id = :predio_id
            ORDER BY codigo
        """)
        vertices_rows = db.execute(q_vertices, {"predio_id": predio_row["id"]}).mappings().all()
        vertices_list = [
            Vertice(
                id=v["id"],
                predio_id=v["predio_id"],
                cod_catastral=v["cod_catastral"],
                codigo=v["codigo"],
                coord_x=float(v["coord_x"]),
                coord_y=float(v["coord_y"]),
                geom_wkt=v["geom_wkt"]
            ) for v in vertices_rows
        ]
        
        q_linderos = text("""
            SELECT id, predio_id, cod_catastral, longitud, rumbo, colindante, ST_AsText(geom) as geom_wkt
            FROM catastro.linea_lindero 
            WHERE predio_id = :predio_id
            ORDER BY id
        """)
        linderos_rows = db.execute(q_linderos, {"predio_id": predio_row["id"]}).mappings().all()
        linderos_list = [
            Lindero(
                id=l["id"],
                predio_id=l["predio_id"],
                cod_catastral=l["cod_catastral"],
                longitud=float(l["longitud"]),
                rumbo=l["rumbo"],
                colindante=l["colindante"],
                geom_wkt=l["geom_wkt"]
            ) for l in linderos_rows
        ]
        
        res = PredioDetalleEspacial(
            predio=predio_data,
            vertices=vertices_list,
            linderos=linderos_list
        )
        print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
