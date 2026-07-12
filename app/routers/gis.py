from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request, UploadFile, File, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
import os
import uuid
import shutil
import zipfile
import subprocess
from osgeo import ogr, osr, gdal
import psycopg2
import logging
import functools
import math

from app.core.database import get_db
from app.routers.users import get_current_user
from app.models import Usuario
from app import schemas
from app.core.ortofoto_service import procesar_ortofoto_background, PROGRESS_STORE
from app.core.catalogacion_service import run_catalogacion_masiva
from app.core.logger import log_audit
import threading

from app.core.file_utils import check_path_exists, get_gdal_path, is_s3_path

base_orto_dir = os.getenv("DIR_ORTOFOTOS_ORIGINALES", r"C:\LNCZ\proyecto-catastro-2026\Ortofotos")
UPLOAD_TEMP_DIR = os.path.join(os.getcwd(), "Temp") if is_s3_path(base_orto_dir) else os.path.join(base_orto_dir, "Temp")
os.makedirs(UPLOAD_TEMP_DIR, exist_ok=True)

router = APIRouter(prefix="/gis", tags=["GIS / Datos Espaciales"])

@router.get("/seleccionar-archivo")
def seleccionar_archivo():
    """
    Abre una ventana de diálogo nativa de Windows para seleccionar un archivo.
    ATENCIÓN: Esto solo funciona si el backend corre localmente (modo 'local').
    En la nube (Render/Linux) esto causaría un error o simplemente no funcionaría.
    """
    import tkinter as tk
    from tkinter import filedialog
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        file_path = filedialog.askopenfilename(
            title="Selecciona la ortofoto (.tif, .ecw, .jp2)",
            filetypes=[("Archivos Raster", "*.tif *.tiff *.ecw *.jp2"), ("Todos los archivos", "*.*")]
        )
        root.destroy()
        
        if not file_path:
            raise HTTPException(status_code=400, detail="No se seleccionó ningún archivo")
            
        return {"ruta": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo abrir el selector: {str(e)}")

from typing import Optional

@router.get("/predios", response_model=schemas.GeoJSONFeatureCollection)
async def get_predios_geojson(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: Any = Depends(get_current_user)
):
    """
    Obtener todos los predios en formato GeoJSON FeatureCollection para el visor del mapa.
    """
    query = text("""
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
        {0}
        {1};
    """.format(
        "AND fecha_creacion >= :fecha_inicio" if fecha_inicio else "",
        "AND fecha_creacion <= :fecha_fin" if fecha_fin else ""
    ))
    try:
        params = {"empresa_id": current_user.id_empresa}
        if fecha_inicio: params["fecha_inicio"] = fecha_inicio
        if fecha_fin: params["fecha_fin"] = fecha_fin
        
        result = db.execute(query, params).scalar_one_or_none()
        return result or {"type": "FeatureCollection", "features": []}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener datos espaciales de predios: {str(e)}"
        )

@router.post("/posesionarios", response_model=schemas.Posesionario, status_code=status.HTTP_201_CREATED)
async def create_posesionario(pos: schemas.PosesionarioBase, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Crear un nuevo posesionario. Si la cédula ya existe, devuelve el existente.
    """
    query_check = text("SELECT id, cedula, nombre FROM catastro.posesionario WHERE cedula = :cedula")
    existing = db.execute(query_check, {"cedula": pos.cedula}).mappings().first()
    if existing:
        return dict(existing)
        
    query = text("""
        INSERT INTO catastro.posesionario (cedula, nombre, empresa_id) 
        VALUES (:cedula, :nombre, :empresa_id) RETURNING id, cedula, nombre;
    """)
    try:
        result = db.execute(query, {
            "cedula": pos.cedula,
            "nombre": pos.nombre,
            "empresa_id": current_user.id_empresa
        }).mappings().first()
        db.commit()
        return dict(result)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/posesionarios/buscar/{cedula}", response_model=schemas.Posesionario)
async def buscar_posesionario(cedula: str, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Buscar un posesionario por su cédula para autocompletar formularios.
    """
    query = text("SELECT id, cedula, nombre FROM catastro.posesionario WHERE cedula = :cedula")
    result = db.execute(query, {"cedula": cedula}).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="Posesionario no encontrado")
    return dict(result)

@router.get("/codigos/buscar/{codigo}", response_model=schemas.CodigoCatastral)
async def buscar_codigo(codigo: str, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Buscar información de un código catastral para autocompletar formularios.
    """
    query = text("""
        SELECT p.cod_catastral as codigo, p.posesionario_id, po.cedula as cedula_posesionario, po.nombre as nombre_posesionario
        FROM catastro.predio p
        LEFT JOIN catastro.posesionario po ON p.posesionario_id = po.id
        WHERE p.cod_catastral = :codigo
    """)
    result = db.execute(query, {"codigo": codigo}).mappings().first()
    if not result:
        raise HTTPException(status_code=404, detail="Código Catastral no encontrado")
    return dict(result)

def _generar_vertices_y_linderos(db: Session, predio_id: int):
    # Primero limpiar si ya existen (para updates)
    db.execute(text("DELETE FROM catastro.vertice WHERE predio_id = :id"), {"id": predio_id})
    db.execute(text("DELETE FROM catastro.linea_lindero WHERE predio_id = :id"), {"id": predio_id})
    
    # Extraer vértices y guardarlos
    query_puntos = text("""
        INSERT INTO catastro.vertice (predio_id, cod_catastral, codigo, coord_x, coord_y, geom, empresa_id)
        SELECT 
            p.id, 
            CASE WHEN EXISTS (SELECT 1 FROM catastro.codigo_catastral cc WHERE cc.codigo = p.cod_catastral) THEN p.cod_catastral ELSE NULL END, 
            'P' || LPAD(i::text, 2, '0'),
            ST_X(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i)),
            ST_Y(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i)),
            ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i),
            p.empresa_id
        FROM catastro.predio p
        CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(p.geom, 1))) - 1) as i
        WHERE p.id = :id
    """)
    db.execute(query_puntos, {"id": predio_id})

    # Extraer líneas (linderos)
    query_lineas = text("""
        INSERT INTO catastro.linea_lindero (predio_id, cod_catastral, longitud, rumbo, colindante, geom, empresa_id)
        SELECT 
            p.id, 
            CASE WHEN EXISTS (SELECT 1 FROM catastro.codigo_catastral cc WHERE cc.codigo = p.cod_catastral) THEN p.cod_catastral ELSE NULL END,
            ST_Length(ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i+1))),
            NULL, -- El rumbo dms puede calcularse después o en otra función
            '', -- Colindante inicial vacío
            ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(p.geom, 1)), i+1)),
            p.empresa_id
        FROM catastro.predio p
        CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(p.geom, 1))) - 1) as i
        WHERE p.id = :id
    """)
    db.execute(query_lineas, {"id": predio_id})

@router.post("/predios", status_code=status.HTTP_201_CREATED)
async def create_predio(predio: schemas.PredioCreate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Crear un nuevo predio ingresando la geometría en formato GeoJSON.
    """
    import json
    geojson_str = json.dumps(predio.geom_geojson)
    
    geom_sql = "ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326), 32717)"
    if predio.es_utm:
        geom_sql = "ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 32717)"
        
    query_codigo = text("""
        INSERT INTO catastro.codigo_catastral (codigo, posesionario_id, empresa_id, activo)
        VALUES (:codigo, :posesionario_id, :empresa_id, true)
        ON CONFLICT (codigo) DO NOTHING;
    """)
    db.execute(query_codigo, {"codigo": predio.cod_catastral, "posesionario_id": predio.posesionario_id, "empresa_id": current_user.id_empresa})

    query = text(f"""
        INSERT INTO catastro.predio (posesionario_id, cod_catastral, geom, area_ha, empresa_id)
        VALUES (:posesionario_id, :cod_catastral, {geom_sql}, ST_Area({geom_sql}) / 10000.0, :empresa_id)
        RETURNING id;
    """)
    try:
        result = db.execute(query, {
            "posesionario_id": predio.posesionario_id,
            "cod_catastral": predio.cod_catastral,
            "geojson": geojson_str,
            "empresa_id": current_user.id_empresa
        })
        new_id = result.scalar()
        
        # Generar linderos y vértices automáticamente
        _generar_vertices_y_linderos(db, new_id)
        
        db.commit()
        log_audit(db, "INFO", "PREDIO_CREATED", f"Predio {new_id} creado por {current_user.username}", current_user.id_usuario)
        return {"message": "Predio creado exitosamente", "id": new_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al crear predio: {str(e)}")

@router.put("/predios/{id}")
async def update_predio(id: int, predio: schemas.PredioUpdate, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Actualizar un predio. Si se envía geometría, se actualiza, lo que dispara los triggers para regenerar linderos.
    """
    import json
    
    updates = []
    params = {"id": id}
    
    if predio.posesionario_id is not None:
        updates.append("posesionario_id = :posesionario_id")
        params["posesionario_id"] = predio.posesionario_id
        
    if predio.cod_catastral is not None:
        updates.append("cod_catastral = :cod_catastral")
        params["cod_catastral"] = predio.cod_catastral
        
        # Asegurar que exista en codigo_catastral
        query_codigo = text("""
            INSERT INTO catastro.codigo_catastral (codigo, activo)
            VALUES (:cod_catastral, true)
            ON CONFLICT (codigo) DO NOTHING;
        """)
        db.execute(query_codigo, {"cod_catastral": predio.cod_catastral})
        
    if predio.estado is not None:
        updates.append("estado = :estado")
        params["estado"] = predio.estado
        
    if predio.geom_geojson is not None:
        updates.append("geom = ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326), 32717)")
        updates.append("area_ha = ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326), 32717)) / 10000.0")
        params["geojson"] = json.dumps(predio.geom_geojson)
        
    if not updates:
        return {"message": "No hay campos para actualizar"}
        
    query = text(f"""
        UPDATE catastro.predio
        SET {', '.join(updates)}
        WHERE id = :id
    """)
    
    try:
        result = db.execute(query, params)
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Predio no encontrado")
            
        if predio.geom_geojson is not None:
            _generar_vertices_y_linderos(db, id)
            
        db.commit()
        log_audit(db, "INFO", "PREDIO_UPDATED", f"Predio {id} actualizado por {current_user.username}", current_user.id_usuario)
        return {"message": "Predio actualizado exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al actualizar predio: {str(e)}")

@router.delete("/predios/{id}")
async def delete_predio(id: int, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Eliminar un predio lógicamente o físicamente dependiendo de la DB.
    """
    query = text("DELETE FROM catastro.predio WHERE id = :id")
    try:
        result = db.execute(query, {"id": id})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Predio no encontrado")
        db.commit()
        log_audit(db, "WARNING", "PREDIO_DELETED", f"Predio {id} eliminado por {current_user.username}", current_user.id_usuario)
        return {"message": "Predio eliminado exitosamente"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Error al eliminar predio: {str(e)}")

@router.get("/vertices", response_model=schemas.GeoJSONFeatureCollection)
async def get_vertices_geojson(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Obtener todos los vértices en formato GeoJSON FeatureCollection.
    """
    query = text("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'id', id,
                    'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json,
                    'properties', json_build_object(
                        'id', id,
                        'predio_id', predio_id,
                        'codigo', codigo,
                        'coord_x', coord_x,
                        'coord_y', coord_y,
                        'cod_catastral', cod_catastral,
                        'estado', estado,
                        'fecha_creacion', fecha_creacion,
                        'fecha_baja', fecha_baja
                    )
                )
            ), '[]'::json)
        )
        FROM catastro.vertice;
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        return result or {"type": "FeatureCollection", "features": []}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener vértices: {str(e)}"
        )

@router.get("/lineas", response_model=schemas.GeoJSONFeatureCollection)
async def get_lineas_geojson(db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """
    Obtener todas las líneas de lindero en formato GeoJSON FeatureCollection.
    """
    query = text("""
        SELECT json_build_object(
            'type', 'FeatureCollection',
            'features', COALESCE(json_agg(
                json_build_object(
                    'type', 'Feature',
                    'id', id,
                    'geometry', ST_AsGeoJSON(ST_Transform(geom, 4326))::json,
                    'properties', json_build_object(
                        'id', id,
                        'predio_id', predio_id,
                        'longitud', longitud,
                        'rumbo', rumbo,
                        'colindante', colindante,
                        'cod_catastral', cod_catastral,
                        'tramo', tramo,
                        'estado', estado,
                        'fecha_creacion', fecha_creacion,
                        'fecha_baja', fecha_baja
                    )
                )
            ), '[]'::json)
        )
        FROM catastro.linea_lindero;
    """)
    try:
        result = db.execute(query).scalar_one_or_none()
        return result or {"type": "FeatureCollection", "features": []}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener linderos: {str(e)}"
        )

@router.get("/predios/detalle/{cod_catastral}", response_model=schemas.PredioDetalleEspacial)
async def get_predio_detalle_completo(cod_catastral: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Obtener el detalle espacial completo de un predio (Polígono, Vértices y Linderos) 
    conectado por el Código Catastral.
    """
    # 1. Obtener datos del predio y su geometría en formato WKT
    q_predio = text("""
        SELECT id, cod_catastral, area_ha, posesionario_id, nombre_posesionario, cedula, estado, fecha_creacion, fecha_baja, predio_padre_id, ST_AsText(geom) as geom_wkt
        FROM catastro.v_predio_completo 
        WHERE cod_catastral = :cod_catastral
    """)
    predio_row = db.execute(q_predio, {"cod_catastral": cod_catastral}).mappings().first()
    if not predio_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Predio catastral no encontrado en el sistema"
        )
        
    predio_id = predio_row["id"]
    
    # 2. Obtener los vértices del predio
    q_vertices = text("""
        SELECT id, predio_id, cod_catastral, codigo, coord_x, coord_y, ST_AsText(geom) as geom_wkt
        FROM catastro.vertice 
        WHERE predio_id = :predio_id
        ORDER BY codigo
    """)
    vertices_rows = db.execute(q_vertices, {"predio_id": predio_id}).mappings().all()
    
    # 3. Obtener las líneas de lindero (lados/tramos)
    q_linderos = text("""
        SELECT id, predio_id, cod_catastral, longitud, rumbo, colindante, ST_AsText(geom) as geom_wkt
        FROM catastro.linea_lindero 
        WHERE predio_id = :predio_id
        ORDER BY id
    """)
    linderos_rows = db.execute(q_linderos, {"predio_id": predio_id}).mappings().all()
    
    # 4. Formatear datos de acuerdo al esquema Pydantic
    predio_data = schemas.Predio(
        id=predio_row["id"],
        cod_catastral=predio_row["cod_catastral"],
        area_ha=float(predio_row["area_ha"]),
        posesionario_id=predio_row["posesionario_id"],
        nombre_posesionario=predio_row["nombre_posesionario"],
        cedula=predio_row["cedula"],
        geom_wkt=predio_row["geom_wkt"]
    )
    
    vertices_list = [
        schemas.Vertice(
            id=v["id"],
            predio_id=v["predio_id"],
            cod_catastral=v["cod_catastral"],
            codigo=v["codigo"],
            coord_x=float(v["coord_x"]),
            coord_y=float(v["coord_y"]),
            geom_wkt=v["geom_wkt"]
        ) for v in vertices_rows
    ]
    
    linderos_list = [
        schemas.Lindero(
            id=l["id"],
            predio_id=l["predio_id"],
            cod_catastral=l["cod_catastral"],
            longitud=float(l["longitud"]),
            rumbo=l["rumbo"],
            colindante=l["colindante"],
            geom_wkt=l["geom_wkt"]
        ) for l in linderos_rows
    ]
    
    return schemas.PredioDetalleEspacial(
        predio=predio_data,
        vertices=vertices_list,
        linderos=linderos_list
    )

@router.get("/predios/detalle-id/{predio_id}", response_model=schemas.PredioDetalleEspacial)
async def get_predio_detalle_por_id(predio_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Obtener el detalle espacial completo de un predio (Polígono, Vértices y Linderos) 
    conectado por el ID del Predio en la base de datos.
    """
    # 1. Obtener datos del predio y su geometría en formato WKT
    q_predio = text("""
        SELECT id, cod_catastral, area_ha, posesionario_id, nombre_posesionario, cedula, ST_AsText(geom) as geom_wkt
        FROM catastro.v_predio_completo 
        WHERE id = :predio_id
    """)
    predio_row = db.execute(q_predio, {"predio_id": predio_id}).mappings().first()
    if not predio_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Predio con ID {predio_id} no encontrado en el sistema"
        )
        
    # 2. Obtener los vértices del predio
    q_vertices = text("""
        SELECT id, predio_id, cod_catastral, codigo, coord_x, coord_y, ST_AsText(geom) as geom_wkt
        FROM catastro.vertice 
        WHERE predio_id = :predio_id
        ORDER BY codigo
    """)
    vertices_rows = db.execute(q_vertices, {"predio_id": predio_id}).mappings().all()
    
    # 3. Obtener las líneas de lindero (lados/tramos)
    q_linderos = text("""
        SELECT id, predio_id, cod_catastral, longitud, rumbo, colindante, ST_AsText(geom) as geom_wkt
        FROM catastro.linea_lindero 
        WHERE predio_id = :predio_id
        ORDER BY id
    """)
    linderos_rows = db.execute(q_linderos, {"predio_id": predio_id}).mappings().all()
    
    # 4. Formatear datos de acuerdo al esquema Pydantic
    predio_data = schemas.Predio(
        id=predio_row["id"],
        cod_catastral=predio_row["cod_catastral"],
        area_ha=float(predio_row["area_ha"]),
        posesionario_id=predio_row["posesionario_id"],
        nombre_posesionario=predio_row["nombre_posesionario"],
        cedula=predio_row["cedula"],
        geom_wkt=predio_row["geom_wkt"]
    )
    
    vertices_list = [
        schemas.Vertice(
            id=v["id"],
            predio_id=v["predio_id"],
            cod_catastral=v["cod_catastral"],
            codigo=v["codigo"],
            coord_x=float(v["coord_x"]),
            coord_y=float(v["coord_y"]),
            geom_wkt=v["geom_wkt"]
        ) for v in vertices_rows
    ]
    
    linderos_list = [
        schemas.Lindero(
            id=l["id"],
            predio_id=l["predio_id"],
            cod_catastral=l["cod_catastral"],
            longitud=float(l["longitud"]),
            rumbo=l["rumbo"],
            colindante=l["colindante"],
            geom_wkt=l["geom_wkt"]
        ) for l in linderos_rows
    ]
    
    return schemas.PredioDetalleEspacial(
        predio=predio_data,
        vertices=vertices_list,
        linderos=linderos_list
    )

@router.get("/codigos-catastrales", response_model=List[schemas.CodigoCatastral])
async def get_codigos_catastrales(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_user)
):
    """
    Obtener la lista de todos los códigos catastrales registrados, incluyendo la cédula y nombre del posesionario.
    """
    query = text("""
        SELECT cc.codigo, cc.activo, cc.fecha_creacion, cc.posesionario_id,
               pos.cedula AS cedula_posesionario, pos.nombre AS nombre_posesionario
        FROM catastro.codigo_catastral cc
        LEFT JOIN catastro.posesionario pos ON cc.posesionario_id = pos.id
        WHERE (CAST(:empresa_id AS INTEGER) IS NULL OR cc.empresa_id = :empresa_id)
        {0}
        {1}
        ORDER BY cc.fecha_creacion DESC
    """.format(
        "AND cc.fecha_creacion >= :fecha_inicio" if fecha_inicio else "",
        "AND cc.fecha_creacion <= :fecha_fin" if fecha_fin else ""
    ))
    try:
        params = {"empresa_id": current_user.id_empresa}
        if fecha_inicio: params["fecha_inicio"] = fecha_inicio
        if fecha_fin: params["fecha_fin"] = fecha_fin
        rows = db.execute(query, params).mappings().all()
        return [
            schemas.CodigoCatastral(
                codigo=r["codigo"],
                activo=r["activo"],
                posesionario_id=r["posesionario_id"],
                fecha_creacion=r["fecha_creacion"],
                cedula_posesionario=r["cedula_posesionario"],
                nombre_posesionario=r["nombre_posesionario"]
            ) for r in rows
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener códigos catastrales: {str(e)}"
        )

@router.post("/codigos-catastrales", response_model=schemas.CodigoCatastral, status_code=status.HTTP_201_CREATED)
async def create_codigo_catastral(payload: schemas.CodigoCatastralBase, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Registrar un nuevo código catastral en la tabla maestra, opcionalmente asociado a un posesionario.
    """
    # Check if exists
    q_check = text("SELECT codigo FROM catastro.codigo_catastral WHERE codigo = :codigo AND empresa_id = :empresa_id")
    exists = db.execute(q_check, {"codigo": payload.codigo, "empresa_id": current_user.id_empresa}).scalar()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El código catastral '{payload.codigo}' ya existe"
        )
    
    # Check if posesionario_id exists if provided
    if payload.posesionario_id:
        q_pos = text("SELECT id FROM catastro.posesionario WHERE id = :id")
        pos_exists = db.execute(q_pos, {"id": payload.posesionario_id}).scalar()
        if not pos_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El posesionario con ID {payload.posesionario_id} no existe"
            )
            
    q_insert = text("""
        INSERT INTO catastro.codigo_catastral (codigo, activo, posesionario_id, empresa_id)
        VALUES (:codigo, :activo, :posesionario_id, :empresa_id)
        RETURNING codigo, activo, posesionario_id, fecha_creacion
    """)
    try:
        res = db.execute(q_insert, {
            "codigo": payload.codigo, 
            "activo": payload.activo,
            "posesionario_id": payload.posesionario_id,
            "empresa_id": current_user.id_empresa
        }).mappings().first()
        
        # Get posesionario details
        cedula_p, nombre_p = None, None
        if payload.posesionario_id:
            q_p_details = text("SELECT cedula, nombre FROM catastro.posesionario WHERE id = :id")
            p_row = db.execute(q_p_details, {"id": payload.posesionario_id}).mappings().first()
            if p_row:
                cedula_p = p_row["cedula"]
                nombre_p = p_row["nombre"]
                
        db.commit()
        return schemas.CodigoCatastral(
            codigo=res["codigo"],
            activo=res["activo"],
            posesionario_id=res["posesionario_id"],
            fecha_creacion=res["fecha_creacion"],
            cedula_posesionario=cedula_p,
            nombre_posesionario=nombre_p
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar código catastral: {str(e)}"
        )

@router.delete("/codigos-catastrales/{codigo}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_codigo_catastral(codigo: str, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Eliminar un código catastral (se eliminarán en cascada los predios, linderos y vértices asociados).
    """
    q_check = text("SELECT codigo FROM catastro.codigo_catastral WHERE codigo = :codigo")
    exists = db.execute(q_check, {"codigo": codigo}).scalar()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El código catastral '{codigo}' no existe"
        )
    
    q_delete = text("DELETE FROM catastro.codigo_catastral WHERE codigo = :codigo")
    try:
        db.execute(q_delete, {"codigo": codigo})
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar código catastral: {str(e)}"
        )

import threading
from app.core.database import SessionLocal

def _run_gdal_thread(task_id: str, ruta_absoluta: str, dpa_data: dict):
    """Wrapper para correr el proceso pesado con su propia conexión DB."""
    db = SessionLocal()
    try:
        procesar_ortofoto_background(task_id, ruta_absoluta, db, dpa_data)
    finally:
        db.close()

@router.post("/ortofotos/procesar", status_code=status.HTTP_202_ACCEPTED)
async def procesar_ortofoto(request: Request):
    """
    Endpoint para procesar una ortofoto y generar sus pirámides en segundo plano.
    Espera un JSON de la forma: {"nombre_archivo": "...", "id_provincia": 1, ...}
    """
    body = await request.json()
    nombre_archivo = body.get("nombre_archivo", "")
    dpa_data = {
        "id_provincia": body.get("id_provincia"),
        "id_canton": body.get("id_canton"),
        "id_ciudad": body.get("id_ciudad")
    }
    
    if not nombre_archivo:
        raise HTTPException(status_code=400, detail="Debe proporcionar el nombre del archivo")
    
    # Construir ruta absoluta
    ruta_absoluta = nombre_archivo
    if not os.path.isabs(nombre_archivo) and not is_s3_path(nombre_archivo):
        base_dir = os.getenv("DIR_ORTOFOTOS_ORIGINALES")
        if not base_dir:
            raise HTTPException(status_code=500, detail="DIR_ORTOFOTOS_ORIGINALES no está configurado en .env")
        ruta_absoluta = get_gdal_path(base_dir, nombre_archivo)
    
    # Check if the path exists (either local or via boto3 for S3)
    # Note: If it's a /vsis3/ path, we can't use check_path_exists easily unless we parse it.
    # We will just assume it's valid, GDAL will fail later if it's not.
    if not is_s3_path(base_dir) and not os.path.exists(ruta_absoluta) and not ruta_absoluta.startswith("/vsis3/"):
        raise HTTPException(status_code=404, detail=f"El archivo no existe en el servidor: {ruta_absoluta}")
        
    # Generar un ID único para rastrear esta tarea
    task_id = str(uuid.uuid4())
    
    # Arrancar GDAL en un hilo 100% independiente para no bloquear el servidor
    hilo = threading.Thread(target=_run_gdal_thread, args=(task_id, ruta_absoluta, dpa_data))
    hilo.daemon = True
    hilo.start()
    
    return {
        "mensaje": f"Procesamiento iniciado en segundo plano para {nombre_archivo}", 
        "ruta": ruta_absoluta,
        "task_id": task_id
    }

@router.get("/ortofotos/progreso/{task_id}")
def obtener_progreso(task_id: str):
    """
    Devuelve el porcentaje de progreso de GDAL (0 a 100).
    Si hay error devuelve -1.
    """
    if task_id not in PROGRESS_STORE:
        return {"progreso": 0, "estado": "esperando"}
        
    progreso = PROGRESS_STORE[task_id]
    estado = "procesando"
    
    if isinstance(progreso, str) and progreso.startswith("ERROR:"):
        return {"progreso": -1, "estado": "error", "detalle": progreso}
        
    if progreso == 100:
        estado = "completado"
    elif progreso < 0:
        estado = "error"
        
    return {"progreso": progreso, "estado": estado}

@router.get("/s3/list")
def list_s3_files(db: Session = Depends(get_db)):
    """Lista las ortofotos en S3 y marca cuáles están procesadas."""
    try:
        from app.core.file_utils import list_ortofotos
        base_dir = os.getenv("DIR_ORTOFOTOS_ORIGINALES", "")
        if not base_dir:
            return {"files": []}
            
        archivos_s3 = list_ortofotos(base_dir)
        
        # Consultar cuáles ya existen en la base de datos
        q = text("SELECT nombre_archivo FROM catastro.ortofotos_catalogo")
        procesados_db = {row[0] for row in db.execute(q).fetchall()}
        
        resultados = []
        for arch in archivos_s3:
            resultados.append({
                "filename": arch,
                "procesado": arch in procesados_db
            })
            
        return {"files": resultados}
    except Exception as e:
        print("Error en /s3/list:", e)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file_drag_drop(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint universal para recibir archivos arrastrados (Drag & Drop).
    Detecta si es Raster (Ortofoto) o Vector (Shapefile Zip / GeoJSON) y lo procesa.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No se envió ningún archivo")

    temp_path = os.path.join(UPLOAD_TEMP_DIR, file.filename)
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    ext = file.filename.split('.')[-1].lower()

    # 1. ES ORTOFOTO
    if ext in ['tif', 'tiff', 'ecw', 'jp2']:
        task_id = str(uuid.uuid4())
        background_tasks.add_task(procesar_ortofoto_background, task_id, temp_path, db)
        return {
            "mensaje": "Ortofoto recibida. Procesando en segundo plano...",
            "task_id": task_id,
            "tipo": "raster"
        }

    # 2. ES VECTOR (Shapefile comprimido o GeoJSON)
    elif ext in ['zip', 'geojson']:
        try:
            target_files = [temp_path]
            extract_dir = None
            
            if ext == 'zip':
                extract_dir = os.path.join(UPLOAD_TEMP_DIR, str(uuid.uuid4()))
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Buscar el .shp
                shp_files = [f for f in os.listdir(extract_dir) if f.endswith('.shp')]
                if not shp_files:
                    raise Exception("No se encontró ningún archivo .shp dentro del ZIP.")
                target_files = [os.path.join(extract_dir, f) for f in shp_files]

            # Abrir con OGR (GDAL)
            ogr.UseExceptions()
            
            features_insertados = 0
            features_actualizados = 0
            capas_procesadas = []
            
            for target_file in target_files:
                ds = ogr.Open(target_file)
                if ds is None:
                    continue
    
                layer = ds.GetLayer()
                geom_type = layer.GetGeomType()
                
                srs = layer.GetSpatialRef()
                srid_origen = 3857 # default asunción
                if srs:
                    srs.AutoIdentifyEPSG()
                    epsg = srs.GetAuthorityCode(None)
                    if epsg: srid_origen = int(epsg)
    
                tipo_detectado = ""
                tabla_destino = ""
                
                if geom_type in [ogr.wkbPolygon, ogr.wkbMultiPolygon, ogr.wkbPolygon25D, ogr.wkbMultiPolygon25D]:
                    tipo_detectado = "Polígonos (Predios)"
                    tabla_destino = "catastro.predio"
                elif geom_type in [ogr.wkbLineString, ogr.wkbMultiLineString, ogr.wkbLineString25D, ogr.wkbMultiLineString25D]:
                    tipo_detectado = "Líneas (Linderos)"
                    tabla_destino = "catastro.linea_lindero"
                elif geom_type in [ogr.wkbPoint, ogr.wkbMultiPoint, ogr.wkbPoint25D, ogr.wkbMultiPoint25D]:
                    tipo_detectado = "Puntos (Vértices)"
                    tabla_destino = "catastro.vertice"
                else:
                    # Ignorar capas no soportadas
                    continue
                    
                capa_nombre = tabla_destino.split('.')[1]
                if capa_nombre not in capas_procesadas:
                    capas_procesadas.append(capa_nombre)
    
                # Insertar o actualizar cada feature
                for feature in layer:
                    geom = feature.GetGeometryRef()
                    if not geom: continue
                    
                    wkt = geom.ExportToWkt()
                    
                    feat_id = None
                    if feature.GetFieldIndex("id") >= 0:
                        feat_id = feature.GetField("id")
                        
                    if feat_id:
                        query = text(f"""
                            UPDATE {tabla_destino} 
                            SET geom = ST_Transform(ST_GeomFromText(:wkt, :srid_origen), 32717)
                            WHERE id = :id
                        """)
                        res = db.execute(query, {"wkt": wkt, "srid_origen": srid_origen, "id": feat_id})
                        if res.rowcount > 0:
                            features_actualizados += 1
                            if tabla_destino == "catastro.predio":
                                _generar_vertices_y_linderos(db, feat_id)
                        else:
                            # Si no existe, lo insertamos solo si es predio (lineas y puntos fallarían por FK)
                            if tabla_destino == "catastro.predio":
                                query = text(f"""
                                    INSERT INTO {tabla_destino} (geom)
                                    VALUES (ST_Transform(ST_GeomFromText(:wkt, :srid_origen), 32717))
                                    RETURNING id
                                """)
                                res_ins = db.execute(query, {"wkt": wkt, "srid_origen": srid_origen})
                                features_insertados += 1
                                new_id = res_ins.scalar()
                                _generar_vertices_y_linderos(db, new_id)
                    else:
                        # Sin ID, inserción nueva (solo si es predio para evitar error de FK)
                        if tabla_destino == "catastro.predio":
                            query = text(f"""
                                INSERT INTO {tabla_destino} (geom)
                                VALUES (ST_Transform(ST_GeomFromText(:wkt, :srid_origen), 32717))
                                RETURNING id
                            """)
                            res_ins = db.execute(query, {"wkt": wkt, "srid_origen": srid_origen})
                            features_insertados += 1
                            new_id = res_ins.scalar()
                            _generar_vertices_y_linderos(db, new_id)

            db.commit()
            
            if extract_dir: shutil.rmtree(extract_dir)
            os.remove(temp_path)
            
            msg = f"Vector procesado. Insertados: {features_insertados}, Actualizados: {features_actualizados}."
            log_audit(db, "INFO", "PROCESAR_VECTOR", msg)
            
            return {
                "mensaje": msg,
                "tipo": "vector",
                "capa": capas_procesadas[0] if capas_procesadas else "predio"
            }
            
        except Exception as e:
            db.rollback()
            log_audit(db, "ERROR", "PROCESAR_VECTOR_FALLIDO", f"Error al procesar vector: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error al procesar vector: {str(e)}")
            
    else:
        os.remove(temp_path)
        log_audit(db, "WARNING", "UPLOAD_FORMATO_INVALIDO", "Intento de subir formato no soportado")
        raise HTTPException(status_code=400, detail="Formato no soportado. Usa .tif, .ecw, .zip (shapefile) o .geojson")

@router.delete("/ortofotos/{filename}")
async def delete_ortofoto(filename: str, db: Session = Depends(get_db), current_user: Any = Depends(get_current_user)):
    """Elimina una ortofoto del servidor y la base de datos."""
    q_search = text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :fname")
    result = db.execute(q_search, {"fname": filename}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Ortofoto no encontrada")
        
    ruta = result[0]
    
    # 1. Eliminar de BD
    q_delete = text("DELETE FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :fname")
    db.execute(q_delete, {"fname": filename})
    db.commit()
    
    # 2. Eliminar archivos
    try:
        if os.path.exists(ruta): os.remove(ruta)
        if os.path.exists(ruta + ".ovr"): os.remove(ruta + ".ovr")
        if os.path.exists(ruta + ".vr"): os.remove(ruta + ".vr")
    except Exception as e:
        print(f"Error borrando archivo: {e}")
        
    # 3. Recrear VRT Maestro
    try:
        from app.core.ortofoto_service import VRT_FILE
        from osgeo import gdal
        gdal.UseExceptions()
        fotos_db = db.execute(text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE tipo_archivo != 'vrt'")).fetchall()
        rutas_vrt = [f[0] for f in fotos_db if os.path.exists(f[0])]
        if rutas_vrt:
            gdal.BuildVRT(VRT_FILE, rutas_vrt)
        elif os.path.exists(VRT_FILE):
            os.remove(VRT_FILE) # Si no quedan ortofotos, borrar el maestro
    except Exception as e:
        print(f"Error reconstruyendo VRT al borrar: {e}")
        
    log_audit(db, "INFO", "ELIMINAR_ORTOFOTO", f"Ortofoto eliminada: {filename}")
        
    return {"mensaje": f"Ortofoto {filename} eliminada correctamente"}

@router.post("/ortofotos/catalogar-masivo")
async def iniciar_catalogacion_masiva(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Inicia el proceso de catalogación masiva (Mosaico y Pirámides) en segundo plano."""
    if not current_user.id_empresa:
        raise HTTPException(status_code=400, detail="Debe seleccionar o pertenecer a una empresa para catalogar")
        
    task_id = run_catalogacion_masiva(db, current_user.id_empresa)
    return {"message": "Proceso de catalogación masiva iniciado", "task_id": task_id}


# --- TILE SERVER (Ortofotos) ---

def get_vrt_path():
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        result = db.execute(text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE nombre_archivo = 'ortofotos.vrt'")).fetchone()
        db.close()
        if result:
            rc = result[0]
            if rc.startswith("s3://"):
                return get_gdal_path(rc)
            elif os.path.exists(rc):
                return rc
    except Exception as e:
        print("Error obteniendo VRT de la BD:", e)
        
    fallback = os.getenv("DIR_ORTOFOTOS_COMPLEMENTOS")
    if fallback:
        return get_gdal_path(fallback, "ortofotos.vrt")
    return None

VRT_FILE = get_vrt_path()

@router.get("/catalog")
def get_catalog(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Devuelve los cuadros rojos del catálogo en formato GeoJSON para pintar en la web"""
    try:
        query = text("""
            SELECT 
                id, 
                nombre_archivo, 
                ruta_completa, 
                ST_AsGeoJSON(ST_Transform(geom, 4326))::json as geometry 
            FROM catastro.ortofotos_catalogo
            WHERE nombre_archivo != 'ortofotos.vrt' AND (CAST(:empresa_id AS INTEGER) IS NULL OR empresa_id = :empresa_id)
        """)
        rows = db.execute(query, {"empresa_id": current_user.id_empresa}).mappings().fetchall()
        
        features = []
        for row in rows:
            feature = {
                "type": "Feature",
                "properties": {
                    "id": row["id"],
                    "nombre_archivo": row["nombre_archivo"],
                    "ruta_completa": row["ruta_completa"]
                },
                "geometry": row["geometry"]
            }
            features.append(feature)
            
        return JSONResponse(content={
            "type": "FeatureCollection",
            "features": features
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def num2deg(xtile, ytile, zoom):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return lon_deg, lat_deg

@functools.lru_cache(maxsize=1024)
def generate_tile_bytes(z: int, x: int, y: int, source_file: str) -> bytes:
    minx, miny = num2deg(x, y + 1, z)
    maxx, maxy = num2deg(x + 1, y, z)
    
    warp_opts = gdal.WarpOptions(
        format="MEM",
        outputBounds=[minx, miny, maxx, maxy],
        outputBoundsSRS="EPSG:4326",
        srcSRS="EPSG:32717",
        dstSRS="EPSG:3857",
        width=256,
        height=256,
        resampleAlg="nearest",
        srcNodata="0",
        dstAlpha=True
    )
    
    ds = gdal.Warp("", source_file, options=warp_opts)
    if ds is None:
        print(f"GDAL Warp failed for {source_file}: {gdal.GetLastErrorMsg()}")
        return None
        
    band_count = ds.RasterCount
    band_list = None
    if band_count > 4:
        band_list = [1, 2, 3, band_count]  
    elif band_count == 4:
        band_list = [1, 2, 3, 4] 
    elif band_count == 3:
        band_list = [1, 2, 3] 
        
    png_opts = gdal.TranslateOptions(format="PNG", bandList=band_list)
    png_path = f"/vsimem/tile_{z}_{x}_{y}_{abs(hash(source_file))}.png"
    png_ds = gdal.Translate(png_path, ds, options=png_opts)
    if png_ds is None:
        print(f"GDAL Translate failed: {gdal.GetLastErrorMsg()}")
        return None
    png_ds = None 
    
    f = gdal.VSIFOpenL(png_path, "rb")
    if f is None: 
        print(f"VSIFOpenL failed: {gdal.GetLastErrorMsg()}")
        return None
    gdal.VSIFSeekL(f, 0, 2)
    size = gdal.VSIFTellL(f)
    gdal.VSIFSeekL(f, 0, 0)
    png_data = gdal.VSIFReadL(1, size, f)
    gdal.VSIFCloseL(f)
    gdal.Unlink(png_path)
    ds = None
    
    return bytes(png_data)

# Cache en memoria para rutas de archivos y no saturar la base de datos por cada tile
_TILE_SOURCE_CACHE = {}

@router.get("/tiles/{z}/{x}/{y}.png")
def get_tile(z: int, x: int, y: int, filename: str = None, db: Session = Depends(get_db)):
    gdal.UseExceptions()
    
    try:
        source_file = VRT_FILE
        if filename:
            if filename in _TILE_SOURCE_CACHE:
                source_file = _TILE_SOURCE_CACHE[filename]
            else:
                base_orig = os.getenv("DIR_ORTOFOTOS_ORIGINALES")
                comp_dir = os.getenv("DIR_ORTOFOTOS_COMPLEMENTOS")
                
                # Check if VRT exists in complementos
                nombre_base = os.path.splitext(filename)[0]
                vrt_name = f"{nombre_base}.vrt"
                
                s3_vrt_path = f"{comp_dir.rstrip('/')}/{vrt_name}" if is_s3_path(comp_dir or "") else os.path.join(comp_dir or "", vrt_name)
                
                if comp_dir and check_path_exists(s3_vrt_path):
                    source_file = get_gdal_path(comp_dir, vrt_name)
                elif base_orig:
                    source_file = get_gdal_path(base_orig, filename)
                else:
                    # Fallback to DB
                    q = text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :fname")
                    result = db.execute(q, {"fname": filename}).fetchone()
                    if result:
                        rc = result[0]
                        source_file = get_gdal_path(rc) if is_s3_path(rc) else rc
                
                _TILE_SOURCE_CACHE[filename] = source_file
                    
        png_data = generate_tile_bytes(z, x, y, source_file)
        
        if not png_data:
            return Response(status_code=404, headers={"Cache-Control": "public, max-age=3600"})
            
        return Response(content=png_data, media_type="image/png", headers={
            "Cache-Control": "public, max-age=604800, immutable"
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response(status_code=500, content=f"Tile error: {str(e)}")



