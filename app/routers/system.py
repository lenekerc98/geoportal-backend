from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.routers.users import get_current_user
from app.models.log import Log

router = APIRouter(
    prefix="/system",
    tags=["system"]
)

@router.get("/logs")
def get_system_logs(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Retorna todos los logs del sistema, ordenados desde el más reciente.
    """
    try:
        # Obtener logs junto con el nombre del usuario si existe
        logs = db.query(Log).order_by(Log.fecha.desc()).limit(500).all()
        
        result = []
        for log in logs:
            username = log.usuario.username if log.usuario else "Sistema"
            result.append({
                "id_log": log.id_log,
                "tipo": log.tipo,
                "accion": log.accion,
                "descripcion": log.descripcion,
                "fecha": log.fecha.isoformat() if log.fecha else None,
                "username": username
            })
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dpa/provincias")
def get_provincias(db: Session = Depends(get_db)):
    try:
        provincias = db.execute(text("SELECT id, nombre FROM catastro.provincias ORDER BY nombre")).fetchall()
        return [{"id": p[0], "nombre": p[1]} for p in provincias]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dpa/cantones")
def get_cantones(provincia_id: int = None, db: Session = Depends(get_db)):
    try:
        if provincia_id:
            cantones = db.execute(text("SELECT id, nombre FROM catastro.cantones WHERE id_provincia=:p ORDER BY nombre"), {"p": provincia_id}).fetchall()
        else:
            cantones = db.execute(text("SELECT id, nombre FROM catastro.cantones ORDER BY nombre")).fetchall()
        return [{"id": c[0], "nombre": c[1]} for c in cantones]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dpa/ciudades")
def get_ciudades(canton_id: int = None, db: Session = Depends(get_db)):
    try:
        if canton_id:
            ciudades = db.execute(text("SELECT id, nombre FROM catastro.ciudades WHERE id_canton=:c ORDER BY nombre"), {"c": canton_id}).fetchall()
        else:
            ciudades = db.execute(text("SELECT id, nombre FROM catastro.ciudades ORDER BY nombre")).fetchall()
        return [{"id": c[0], "nombre": c[1]} for c in ciudades]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
