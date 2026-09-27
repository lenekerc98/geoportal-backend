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
                "username": username,
                "correo_enviado": getattr(log, 'correo_enviado', None)
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

class DatabaseCloneRequest(BaseModel):
    direction: str = "prod_to_test"  # "prod_to_test" o "test_to_prod"
    confirmacion: Optional[str] = None


def _find_pg_tool(name: str) -> Optional[str]:
    # Priorizar siempre la versión nativa de PostgreSQL instalada (ej: 18.3) para evitar conflictos de versión con QGIS
    for v in ["18", "17", "16", "15", "14"]:
        candidate = rf"C:\Program Files\PostgreSQL\{v}\bin\{name}.exe"
        if os.path.exists(candidate):
            return candidate
        pgadmin_candidate = rf"C:\Program Files\PostgreSQL\{v}\pgAdmin 4\runtime\{name}.exe"
        if os.path.exists(pgadmin_candidate):
            return pgadmin_candidate
    import shutil
    p = shutil.which(name)
    if p:
        return p
    return None


@router.post("/database-clone")
def clone_database(
    req: DatabaseCloneRequest,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Permite al Superadmin sincronizar o refrescar las bases de datos en AWS RDS:
    - 'prod_to_test': Copia la producción oficial (catastro-db) hacia la de prueba (catastro-db-test).
    - 'test_to_prod': Copia la base de prueba (catastro-db-test) hacia la oficial de producción (catastro-db).
    """
    from app.core.database import is_superadmin_request, engine_prod, engine_test
    import subprocess

    is_super = is_superadmin_request(request)
    if not is_super:
        role_name = current_user.rol.nombre.lower() if getattr(current_user, 'rol', None) else ""
        if role_name not in ["superadmin", "superadministrador"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el Superadministrador puede sincronizar las bases de datos."
            )

    url_prod = os.getenv("DATABASE_URL_PROD") or os.getenv("DATABASE_URL")
    url_test = os.getenv("DATABASE_URL_TEST")

    if not url_prod or not url_test:
        raise HTTPException(
            status_code=500,
            detail="Las variables de entorno DATABASE_URL_PROD y DATABASE_URL_TEST deben estar configuradas."
        )

    direction = req.direction.lower().strip()
    if direction == "prod_to_test":
        source = url_prod
        dest = url_test
        direction_msg = "Producción ➔ Prueba"
        dest_engine = engine_test
    elif direction == "test_to_prod":
        if req.confirmacion != "SINCRONIZAR_A_PRODUCCION":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmación de seguridad requerida para sincronizar hacia producción (código: SINCRONIZAR_A_PRODUCCION)."
            )
        source = url_test
        dest = url_prod
        direction_msg = "Prueba ➔ Producción"
        dest_engine = engine_prod
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dirección no válida: '{req.direction}'. Debe ser 'prod_to_test' o 'test_to_prod'."
        )

    pg_dump = _find_pg_tool("pg_dump")
    psql = _find_pg_tool("psql")

    if not pg_dump or not psql:
        raise HTTPException(
            status_code=500,
            detail=f"Herramientas de PostgreSQL (pg_dump / psql) no encontradas en el sistema. pg_dump={pg_dump}, psql={psql}"
        )

    try:
        # 1. Dropear vista dependiente en la BD destino antes del restore para evitar conflictos de DROP TABLE
        with dest_engine.connect() as conn:
            conn.execute(text("DROP VIEW IF EXISTS catastro.v_predio_completo CASCADE"))
            conn.commit()

        # 2. Ejecutar dump y restore de los esquemas requeridos mediante archivo temporal seguro (sin riesgo de bloqueo por tuberías)
        import tempfile
        import uuid
        temp_sql = os.path.join(tempfile.gettempdir(), f"dump_sync_{uuid.uuid4().hex[:8]}.sql")
        try:
            cmd_dump = [
                pg_dump,
                f"--dbname={source}",
                "--schema=seguridad",
                "--schema=catastro",
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "-f", temp_sql
            ]
            res_dump = subprocess.run(cmd_dump, capture_output=True, text=True, timeout=120)
            if res_dump.returncode != 0:
                raise RuntimeError(f"Error en pg_dump: {res_dump.stderr}")

            cmd_restore = [
                psql,
                f"--dbname={dest}",
                "-v", "ON_ERROR_STOP=0",
                "-f", temp_sql
            ]
            res_restore = subprocess.run(cmd_restore, capture_output=True, text=True, timeout=180)
            if res_restore.returncode != 0 and "error" in (res_restore.stderr or "").lower():
                logging.warning(f"Avisos durante psql restore: {res_restore.stderr}")
        finally:
            if os.path.exists(temp_sql):
                try:
                    os.remove(temp_sql)
                except Exception:
                    pass

        # 3. Recrear la vista v_predio_completo en la base destino
        with dest_engine.connect() as conn:
            conn.execute(text("""
                CREATE OR REPLACE VIEW catastro.v_predio_completo AS
                SELECT 
                    p.id,
                    p.cod_catastral,
                    p.posesionario_id,
                    p.empresa_id,
                    p.proyecto_id,
                    p.area_ha,
                    p.geom,
                    p.estado,
                    p.fecha_creacion,
                    p.fecha_baja,
                    p.predio_padre_id,
                    pos.cedula,
                    pos.nombre AS nombre_posesionario
                FROM catastro.predio p
                LEFT JOIN catastro.posesionario pos ON p.posesionario_id = pos.id
            """))
            conn.commit()

        # 4. Obtener conteo actualizado de ambas bases
        with engine_prod.connect() as cp:
            c_prod = cp.execute(text("SELECT count(*) FROM catastro.predio")).scalar() or 0
        with engine_test.connect() as ct:
            c_test = ct.execute(text("SELECT count(*) FROM catastro.predio")).scalar() or 0

        return {
            "status": "ok",
            "message": f"Base de datos sincronizada exitosamente ({direction_msg}).",
            "direction": direction,
            "predios_prod": c_prod,
            "predios_test": c_test
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error durante la sincronización: {str(e)}")


class PurgeCatastroRequest(BaseModel):
    empresa_id: Optional[int] = None
    eliminar_predios: bool = True
    eliminar_posesionarios: bool = True
    confirmacion: str


@router.get("/purge-stats")
def get_purge_stats(
    request: Request,
    empresa_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Retorna el conteo actual de predios, posesionarios, vértices y linderos para una empresa o global.
    Exclusivo para Superadministradores.
    """
    from app.core.database import is_superadmin_request
    if not is_superadmin_request(request):
        role_name = current_user.rol.nombre.lower() if getattr(current_user, 'rol', None) else ""
        if role_name not in ["superadmin", "superadministrador"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: solo el Superadministrador puede acceder a la purga de datos.")

    try:
        p_count = db.execute(
            text("SELECT count(*) FROM catastro.predio WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
            {"emp_id": empresa_id}
        ).scalar() or 0

        pos_count = db.execute(
            text("SELECT count(*) FROM catastro.posesionario WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
            {"emp_id": empresa_id}
        ).scalar() or 0

        v_count = db.execute(
            text("SELECT count(*) FROM catastro.vertice WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
            {"emp_id": empresa_id}
        ).scalar() or 0

        l_count = db.execute(
            text("SELECT count(*) FROM catastro.linea_lindero WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
            {"emp_id": empresa_id}
        ).scalar() or 0

        cc_count = db.execute(
            text("SELECT count(*) FROM catastro.codigo_catastral WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
            {"emp_id": empresa_id}
        ).scalar() or 0

        return {
            "predios": p_count,
            "posesionarios": pos_count,
            "vertices": v_count,
            "linderos": l_count,
            "codigos_catastrales": cc_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener estadísticas de catastro: {str(e)}")


@router.post("/purge-catastro")
def purge_catastro(
    payload: PurgeCatastroRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Eliminación masiva de predios, posesionarios y elementos topológicos.
    Exclusivo para Superadministradores con confirmación textual obligatoria.
    """
    from app.core.database import is_superadmin_request
    if not is_superadmin_request(request):
        role_name = current_user.rol.nombre.lower() if getattr(current_user, 'rol', None) else ""
        if role_name not in ["superadmin", "superadministrador"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado: solo el Superadministrador puede ejecutar la eliminación masiva.")

    if payload.confirmacion.strip().upper() != "ELIMINAR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe escribir exactamente la palabra 'ELIMINAR' para autorizar el borrado.")

    if not payload.eliminar_predios and not payload.eliminar_posesionarios:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Debe seleccionar al menos una opción a eliminar (Predios o Posesionarios).")

    emp_id = payload.empresa_id
    deleted_info = {
        "predios": 0,
        "posesionarios": 0,
        "vertices": 0,
        "linderos": 0,
        "codigos_catastrales": 0
    }

    try:
        # 1. Eliminar Predios y dependencias topológicas
        if payload.eliminar_predios:
            # Romper autorreferencia de predio_padre_id
            db.execute(
                text("UPDATE catastro.predio SET predio_padre_id = NULL WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                {"emp_id": emp_id}
            )
            # Vértices
            res_v = db.execute(
                text("DELETE FROM catastro.vertice WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                {"emp_id": emp_id}
            )
            deleted_info["vertices"] = res_v.rowcount

            # Linderos
            res_l = db.execute(
                text("DELETE FROM catastro.linea_lindero WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                {"emp_id": emp_id}
            )
            deleted_info["linderos"] = res_l.rowcount

            # Historial de predios si existe
            try:
                db.execute(
                    text("DELETE FROM catastro.predio_historial WHERE predio_id IN (SELECT id FROM catastro.predio WHERE :emp_id IS NULL OR empresa_id = :emp_id)"),
                    {"emp_id": emp_id}
                )
            except Exception:
                pass

            # Predios
            res_p = db.execute(
                text("DELETE FROM catastro.predio WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                {"emp_id": emp_id}
            )
            deleted_info["predios"] = res_p.rowcount

            # Códigos catastrales (se eliminan los de la empresa o cualquier huérfano sin predio)
            res_cc = db.execute(
                text("""
                    DELETE FROM catastro.codigo_catastral 
                    WHERE (:emp_id IS NULL OR empresa_id = :emp_id)
                       OR NOT EXISTS (SELECT 1 FROM catastro.predio p WHERE p.cod_catastral = catastro.codigo_catastral.codigo)
                """),
                {"emp_id": emp_id}
            )
            deleted_info["codigos_catastrales"] = res_cc.rowcount

        # 2. Eliminar Posesionarios (personas)
        if payload.eliminar_posesionarios:
            # Si no se eliminaron predios/códigos, desvincular posesionarios para evitar fallas de FK
            if not payload.eliminar_predios:
                db.execute(
                    text("UPDATE catastro.predio SET posesionario_id = NULL WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                    {"emp_id": emp_id}
                )
                db.execute(
                    text("UPDATE catastro.codigo_catastral SET posesionario_id = NULL WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                    {"emp_id": emp_id}
                )

            # Posesionarios (catálogo de personas)
            res_pos = db.execute(
                text("DELETE FROM catastro.posesionario WHERE (:emp_id IS NULL OR empresa_id = :emp_id)"),
                {"emp_id": emp_id}
            )
            deleted_info["posesionarios"] = res_pos.rowcount

        db.commit()

        # Auditoría del sistema
        db_env = (request.headers.get("X-Database-Env") or "prod").upper()
        empresa_desc = f"empresa ID {emp_id}" if emp_id else "TODAS las empresas"
        detalle_audit = (
            f"Purga masiva ejecutada en base [{db_env}] para {empresa_desc}. "
            f"Predios: {deleted_info['predios']}, Posesionarios: {deleted_info['posesionarios']}, "
            f"Vértices: {deleted_info['vertices']}, Linderos: {deleted_info['linderos']}."
        )

        try:
            log_audit(
                db=db,
                tipo="CRITICAL",
                accion="PURGA_MASIVA_CATASTRO",
                descripcion=detalle_audit,
                id_usuario=current_user.id_usuario
            )
        except Exception:
            pass

        return {
            "status": "ok",
            "message": "Eliminación masiva completada exitosamente.",
            "deleted": deleted_info
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error durante la eliminación masiva: {str(e)}")
