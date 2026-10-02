import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import timedelta

from app.core.database import get_db
from app.core import security
from app.models import Usuario
from app import schemas
from app.core.security import ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.logger import log_audit

router = APIRouter(tags=["Autenticación"])


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Buscar el usuario en la base de datos
    clean_username = form_data.username.strip()
    user = db.query(Usuario).filter(func.lower(Usuario.username) == func.lower(clean_username)).first()
    
    # Verificar credenciales
    if not user or not security.verify_password(form_data.password, user.password_hash):
        log_audit(db, "WARNING", "LOGIN_FAILED", f"Intento fallido: usuario {form_data.username} incorrecto.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    token_minutes = max(ACCESS_TOKEN_EXPIRE_MINUTES, 43200)
    access_token_expires = timedelta(minutes=token_minutes)
    
    # Obtener el nombre del rol y permisos para incluirlos en el token
    role_name = user.rol.nombre if user.rol else "user"
    user_permisos = user.rol.permisos if (user.rol and user.rol.permisos) else {}

    default_center = user.empresa.parametros.get("defaultCenter") if user.empresa and user.empresa.parametros else None
    access_token = security.create_access_token(
        data={
            "sub": user.username,
            "role": role_name,
            "empresa_id": user.id_empresa,
            "defaultCenter": default_center,
            "permisos": user_permisos
        },
        expires_delta=access_token_expires
    )
    
    log_audit(db, "INFO", "LOGIN_SUCCESS", f"Sesión iniciada exitosamente por {form_data.username}.")
    return {"access_token": access_token, "token_type": "bearer"}

from pydantic import BaseModel
from typing import Optional
from fastapi import Request

class BrigadistaLoginRequest(BaseModel):
    nombre: str
    apellido: str
    dispositivo_uuid: str
    dispositivo_modelo: Optional[str] = "Móvil Android"

@router.post("/login-brigadista")
def login_brigadista(req: BrigadistaLoginRequest, request: Request, db: Session = Depends(get_db)):
    from sqlalchemy import text
    
    ip = request.client.host if request.client else "0.0.0.0"
    if "x-forwarded-for" in request.headers:
        ip = request.headers["x-forwarded-for"].split(",")[0].strip()

    # Buscar empresa Urdaneta (id 2 o ILIKE '%urdaneta%')
    emp = db.execute(text("SELECT id, nombre FROM catastro.empresa WHERE nombre ILIKE '%urdaneta%' LIMIT 1")).fetchone()
    emp_id = emp[0] if emp else 2
    emp_nombre = emp[1] if emp else "Gobierno Autónomo Descentralizado Urdaneta."

    # Proyecto de Urdaneta (ej. id 3 'Censo Catastral Rural')
    proj = db.execute(text("""
        SELECT p.id, p.nombre 
        FROM catastro.proyecto p
        JOIN catastro.empresa_proyecto ep ON ep.proyecto_id = p.id
        WHERE ep.empresa_id = :emp_id
        LIMIT 1
    """), {"emp_id": emp_id}).fetchone()

    if not proj:
        proj = db.execute(text("SELECT id, nombre FROM catastro.proyecto WHERE estado = 'Activo' ORDER BY id ASC LIMIT 1")).fetchone()

    proj_id = proj[0] if proj else 3
    proj_nombre = proj[1] if proj else "Censo Catastral Urdaneta"

    nombre_clean = req.nombre.strip()
    apellido_clean = req.apellido.strip()
    uuid_clean = req.dispositivo_uuid.strip()

    existente = db.execute(text("""
        SELECT id FROM seguridad.operador_temporal 
        WHERE dispositivo_uuid = :uuid AND nombre ILIKE :nom AND apellido ILIKE :ape
    """), {"uuid": uuid_clean, "nom": nombre_clean, "ape": apellido_clean}).fetchone()

    if existente:
        op_id = existente[0]
        db.execute(text("""
            UPDATE seguridad.operador_temporal 
            SET ultimo_acceso = CURRENT_TIMESTAMP, ip_registro = :ip, dispositivo_modelo = :mod,
                empresa_id = :eid, proyecto_id = :pid, activo = true
            WHERE id = :id
        """), {"ip": ip, "mod": req.dispositivo_modelo, "eid": emp_id, "pid": proj_id, "id": op_id})
    else:
        ins = db.execute(text("""
            INSERT INTO seguridad.operador_temporal (nombre, apellido, dispositivo_uuid, dispositivo_modelo, ip_registro, empresa_id, proyecto_id)
            VALUES (:nom, :ape, :uuid, :mod, :ip, :eid, :pid)
            RETURNING id
        """), {
            "nom": nombre_clean,
            "ape": apellido_clean,
            "uuid": uuid_clean,
            "mod": req.dispositivo_modelo,
            "ip": ip,
            "eid": emp_id,
            "pid": proj_id
        })
        op_id = ins.scalar()

    db.commit()

    nombre_completo = f"{nombre_clean} {apellido_clean}"
    username_sub = f"brigadista_{op_id}"

    # Token con 30 días para que no se cierre en campo
    expires_delta = timedelta(days=30)
    access_token = security.create_access_token(
        data={
            "sub": username_sub,
            "role": "brigadista",
            "operador_temporal_id": op_id,
            "nombre": nombre_completo,
            "empresa_id": emp_id,
            "proyecto_id": proj_id,
            "permisos": {"crear_predio": True, "ver_predio": True}
        },
        expires_delta=expires_delta
    )

    log_audit(db, "INFO", "LOGIN_BRIGADISTA", f"Brigadista {nombre_completo} ingresó desde {ip} ({req.dispositivo_modelo or 'Móvil'}).")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": "brigadista",
        "username": username_sub,
        "nombre": nombre_completo,
        "empresaId": emp_id,
        "empresaNombre": emp_nombre,
        "activeProyectoId": proj_id,
        "activeProyectoNombre": proj_nombre,
        "operador_temporal_id": op_id
    }
