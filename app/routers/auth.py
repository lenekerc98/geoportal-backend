import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
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
    user = db.query(Usuario).filter(Usuario.username == form_data.username).first()
    
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
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Obtener el nombre del rol para incluirlo en el token
    role_name = user.rol.nombre if user.rol else "user"

    access_token = security.create_access_token(
        data={"sub": user.username, "role": role_name, "empresa_id": user.id_empresa}, expires_delta=access_token_expires
    )
    
    log_audit(db, "INFO", "LOGIN_SUCCESS", f"Sesión iniciada exitosamente por {form_data.username}.")
    return {"access_token": access_token, "token_type": "bearer"}
