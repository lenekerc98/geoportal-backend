import os
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

@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    health_status = {
        "api": "OK",
        "database": "ERROR",
        "storage": "ERROR",
        "storage_mode": os.getenv("VITE_STORAGE_MODE", "local")
    }

    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "OK"
    except Exception as e:
        health_status["database"] = f"ERROR: {str(e)}"

    # Check Storage
    try:
        storage_mode = os.getenv("VITE_STORAGE_MODE", "local")
        if storage_mode == "s3":
            s3_bucket = os.getenv("AWS_S3_BUCKET")
            if not s3_bucket:
                health_status["storage"] = "ERROR: AWS_S3_BUCKET not configured"
            else:
                # Basic check, just assume ok if configured or do a boto3 test if needed
                health_status["storage"] = "OK"
        else:
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
            if os.path.exists(upload_dir) and os.access(upload_dir, os.W_OK):
                health_status["storage"] = "OK"
            else:
                health_status["storage"] = "ERROR: Local upload dir not writable or missing"
    except Exception as e:
        health_status["storage"] = f"ERROR: {str(e)}"

    return health_status

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
