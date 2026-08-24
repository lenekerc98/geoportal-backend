import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any
from app.core.database import get_db
from app.routers.users import get_current_user
from app.models import Usuario

router = APIRouter(prefix="/dibujo", tags=["Capa de Dibujo"])

@router.get("/")
def obtener_capa_dibujo(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Obtiene todos los bosquejos del usuario actual"""
    query = text("""
        SELECT id, tipo, ST_AsGeoJSON(ST_Transform(geom, 4326)) as geom 
        FROM catastro.capa_dibujo 
        WHERE usuario_id = :usuario_id
    """)
    result = db.execute(query, {"usuario_id": current_user.id_usuario}).fetchall()
    
    features = []
    for row in result:
        geom_obj = json.loads(row.geom) if isinstance(row.geom, str) else row.geom
        features.append({
            "type": "Feature",
            "properties": {"id": row.id, "tipo": row.tipo},
            "geometry": geom_obj
        })
    return {"type": "FeatureCollection", "features": features}

@router.post("/")
def guardar_dibujo(payload: Dict[Any, Any], db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Guarda un nuevo bosquejo temporal"""
    geom_type = payload.get("tipo") # Point, LineString, Polygon
    geojson = payload.get("geom") # String o dict
    
    if not geom_type or not geojson:
        raise HTTPException(status_code=400, detail="Faltan datos de geometría")
        
    geojson_str = json.dumps(geojson) if isinstance(geojson, dict) else str(geojson)
    
    query = text("""
        INSERT INTO catastro.capa_dibujo (tipo, geom, usuario_id)
        VALUES (:tipo, ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326), 32717), :usuario_id)
        RETURNING id
    """)
    try:
        res = db.execute(query, {
            "tipo": geom_type,
            "geom": geojson_str,
            "usuario_id": current_user.id_usuario
        })
        db.commit()
        return {"success": True, "id": res.fetchone()[0]}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
def eliminar_dibujo(id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """Elimina un bosquejo temporal"""
    query = text("DELETE FROM catastro.capa_dibujo WHERE id = :id AND usuario_id = :usuario_id")
    db.execute(query, {"id": id, "usuario_id": current_user.id_usuario})
    db.commit()
    return {"success": True}

