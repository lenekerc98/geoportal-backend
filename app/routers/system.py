import os
from fastapi import APIRouter, Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db
from app.routers.users import get_current_user
from app.models.log import Log
from app.core.logger import log_audit
from pydantic import BaseModel
from typing import Optional

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
        "storage_mode": os.getenv("STORAGE_MODE", "local")
    }

    # Check Database
    try:
        db.execute(text("SELECT 1"))
        health_status["database"] = "OK"
    except Exception as e:
        health_status["database"] = f"ERROR: {str(e)}"

    # Check Storage
    try:
        storage_mode = os.getenv("STORAGE_MODE", "local")
        if storage_mode == "s3":
            s3_bucket = os.getenv("AWS_S3_BUCKET")
            if not s3_bucket:
                health_status["storage"] = "ERROR: AWS_S3_BUCKET not configured"
            else:
                # Basic check, just assume ok if configured or do a boto3 test if needed
                health_status["storage"] = "OK"
        else:
            upload_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
            if not os.path.exists(upload_dir):
                try:
                    os.makedirs(upload_dir, exist_ok=True)
                except Exception:
                    pass
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
    Retorna todos los logs del sistema (requiere Administrador o Superadmin).
    """
    if not current_user.rol or current_user.rol.nombre.lower() not in ["superadmin", "superadministrador", "admin", "administrador"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: se requiere rol de Administrador")
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
        provincias = db.execute(text("SELECT id, codigo_dpa, nombre FROM catastro.provincias ORDER BY codigo_dpa")).fetchall()
        return [{"id": p[0], "codigo_dpa": p[1], "nombre": p[2]} for p in provincias]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dpa/cantones")
def get_cantones(provincia_id: int = None, db: Session = Depends(get_db)):
    try:
        if provincia_id:
            cantones = db.execute(text("SELECT id, codigo_dpa, nombre FROM catastro.cantones WHERE id_provincia=:p ORDER BY codigo_dpa"), {"p": provincia_id}).fetchall()
        else:
            cantones = db.execute(text("SELECT id, codigo_dpa, nombre FROM catastro.cantones ORDER BY codigo_dpa")).fetchall()
        return [{"id": c[0], "codigo_dpa": c[1], "nombre": c[2]} for c in cantones]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dpa/ciudades")
def get_ciudades(canton_id: int = None, db: Session = Depends(get_db)):
    try:
        if canton_id:
            ciudades = db.execute(text("SELECT id, codigo_dpa, nombre FROM catastro.ciudades WHERE id_canton=:c ORDER BY codigo_dpa"), {"c": canton_id}).fetchall()
        else:
            ciudades = db.execute(text("SELECT id, codigo_dpa, nombre FROM catastro.ciudades ORDER BY codigo_dpa")).fetchall()
        return [{"id": c[0], "codigo_dpa": c[1], "nombre": c[2]} for c in ciudades]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class FrontendErrorReport(BaseModel):
    error: str
    user: Optional[str] = "Anónimo / Sesión frontend"
    url: Optional[str] = ""

import time
_LAST_FRONTEND_ALERT = 0

@router.post("/report-error")
def report_frontend_error(data: FrontendErrorReport, db: Session = Depends(get_db)):
    """
    Recibe un error fatal del frontend, lo registra en la bitácora y envía alerta por correo SMTP con rate-limiting.
    """
    global _LAST_FRONTEND_ALERT
    now = time.time()
    # Limitar envío de correos a máximo 1 cada 2 minutos para evitar saturación SMTP
    debe_enviar_alerta = (now - _LAST_FRONTEND_ALERT) > 120
    if debe_enviar_alerta:
        _LAST_FRONTEND_ALERT = now

    url_safe = str(data.url or '')[:255]
    user_safe = str(data.user or '')[:100]
    error_safe = str(data.error or '')[:1500]

    descripcion = f"Falla Crítica en Frontend:\nURL: {url_safe}\nUsuario: {user_safe}\n\nDetalle del Error:\n{error_safe}"
    log_audit(
        db=db,
        tipo="CRITICAL",
        accion="Falla Crítica Frontend",
        descripcion=descripcion,
        enviar_alerta=debe_enviar_alerta
    )
    return {"status": "ok", "message": "Error reportado"}


@router.get("/database-info")
def get_database_info(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retorna información de las bases de datos en AWS RDS:
    - Estado de producción (catastro-db)
    - Estado de prueba (catastro-db-test)
    - Entorno actual que está utilizando el usuario consultante.
    """
    from app.core.database import engine_prod, engine_test, is_superadmin_request
    from sqlalchemy import text

    is_super = is_superadmin_request(request)
    requested_env = (request.headers.get("X-Database-Env") or "").lower().strip()
    active_env = "test" if (is_super and requested_env == "test") else "prod"

    prod_info = {"name": "catastro-db", "status": "UNKNOWN", "predios": 0}
    test_info = {"name": "catastro-db-test", "status": "UNKNOWN", "predios": 0}

    # Verificar Prod
    try:
        with engine_prod.connect() as conn:
            c = conn.execute(text("SELECT count(*) FROM catastro.predio")).scalar()
            prod_info["status"] = "ONLINE"
            prod_info["predios"] = c
    except Exception as e:
        prod_info["status"] = f"ERROR: {str(e)}"

    # Verificar Test
    try:
        with engine_test.connect() as conn:
            c = conn.execute(text("SELECT count(*) FROM catastro.predio")).scalar()
            test_info["status"] = "ONLINE"
            test_info["predios"] = c
    except Exception as e:
        test_info["status"] = f"ERROR: {str(e)}"

    return {
        "active_env": active_env,
        "is_superadmin": is_super,
        "host": "catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com",
        "databases": {
            "prod": prod_info,
            "test": test_info
        }
    }

@router.post("/database-clone")
def clone_production_to_test(
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Permite al Superadmin sincronizar o refrescar la base de pruebas (catastro-db-test)
    a partir de la base de producción oficial (catastro-db) en AWS RDS.
    """
    from app.core.database import is_superadmin_request
    import subprocess

    if not is_superadmin_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el Superadministrador puede clonar o reiniciar la base de prueba."
        )

    pg_dump = r"C:\Program Files\PostgreSQL8in\pg_dump.exe"
    psql = r"C:\Program Files\PostgreSQL8in\psql.exe"
    source = "postgresql://postgres:L3n3k3rx98.@catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com:5432/catastro-db"
    dest = "postgresql://postgres:L3n3k3rx98.@catastro-db.c09cqw60mwqw.us-east-1.rds.amazonaws.com:5432/catastro-db-test"

    try:
        # Ejecutar dump y restore de los esquemas requeridos
        p1 = subprocess.Popen([pg_dump, f"--dbname={source}", "--schema=seguridad", "--schema=catastro", "--clean", "--if-exists", "--no-owner", "--no-privileges"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen([psql, f"--dbname={dest}", "-q"], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.stdout.close()
        out, err = p2.communicate(timeout=180)

        if p2.returncode != 0:
            raise Exception(err.decode('utf-8', errors='ignore'))

        return {"status": "ok", "message": "Base de datos de prueba clonada exitosamente desde producción."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante el clonado: {str(e)}")
