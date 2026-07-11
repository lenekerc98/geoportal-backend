from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text
from jose import JWTError, jwt
from typing import List
import os
import re

from app.core.database import get_db
from app.core import security
from app.models import Usuario, Rol
from app import schemas
from app.core.logger import log_audit

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

router = APIRouter(tags=["Usuarios"])

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, security.SECRET_KEY, algorithms=[security.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None:
        raise credentials_exception
        
    return user

@router.get("/users/me/", response_model=schemas.Usuario)
async def read_users_me(current_user: Usuario = Depends(get_current_user)):
    return current_user

@router.get("/tools")
async def get_allowed_tools(current_user: Usuario = Depends(get_current_user)):
    """
    Retorna la lista de herramientas permitidas según el rol del usuario.
    """
    role_name = current_user.rol.nombre if current_user.rol else "usuario"
    
    # Por defecto, todos tienen acceso a estas herramientas
    allowed_tools = ["catastro2026:creardibujo"]
    
    if role_name == "admin":
        # Admin tiene acceso a herramientas extra
        allowed_tools.extend(["catastro2026:configurarempresa", "catastro2026:gestionusuarios"])
        
    return {"tools": allowed_tools, "role": role_name}

# --- CRUD de Usuarios ---

@router.get("/users", response_model=List[schemas.Usuario])
async def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Obtener todos los usuarios.
    """
    users = db.query(Usuario).offset(skip).limit(limit).all()
    return users

@router.get("/users/{id_usuario}", response_model=schemas.Usuario)
async def read_user(id_usuario: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Obtener un usuario específico por su ID.
    """
    db_user = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

@router.post("/users", response_model=schemas.Usuario, status_code=status.HTTP_201_CREATED)
async def create_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Crear un nuevo usuario. También crea un usuario correspondiente en PostgreSQL con permisos.
    """
    # Validar que el nombre de usuario sea seguro para sentencias SQL
    if not re.match(r"^[a-zA-Z0-9_]+$", user.username):
        raise HTTPException(
            status_code=400,
            detail="El nombre de usuario solo puede contener letras, números y guiones bajos (sin espacios ni caracteres especiales)"
        )

    # Verificar si el usuario ya existe en la base de datos de la app
    db_user = db.query(Usuario).filter(Usuario.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
    
    # Verificar si el rol especificado existe
    db_role = db.query(Rol).filter(Rol.id_rol == user.id_rol).first()
    if not db_role:
        raise HTTPException(status_code=400, detail="El rol especificado no existe")
        
    hashed_password = security.get_password_hash(user.password)
    
    # Lógica de multitenant:
    # Si es Superadmin, puede asignar a cualquier empresa o a ninguna (None)
    # Si es Admin, obligatoriamente se le asigna la misma empresa que tiene el Admin
    empresa_asignar = user.id_empresa
    if current_user.rol and current_user.rol.nombre.lower() == "admin":
        empresa_asignar = current_user.id_empresa
        
    new_user = Usuario(
        username=user.username,
        password_hash=hashed_password,
        id_rol=user.id_rol,
        id_empresa=empresa_asignar,
        activo=True
    )
    db.add(new_user)
    
    # Sincronizar con usuarios de PostgreSQL
    try:
        # Crear usuario en PostgreSQL con la contraseña plana provista
        db.execute(text(f"CREATE USER {user.username} WITH PASSWORD :password"), {"password": user.password})
        db.execute(text(f"GRANT USAGE ON SCHEMA seguridad TO {user.username}"))
        db.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA seguridad TO {user.username}"))
        db.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA seguridad TO {user.username}"))
        db.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA seguridad GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {user.username}"))
        db.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA seguridad GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {user.username}"))
    except Exception as e:
        # Si el usuario ya existe en PostgreSQL, intentar actualizar contraseña y otorgar permisos
        try:
            db.execute(text(f"ALTER USER {user.username} WITH PASSWORD :password"), {"password": user.password})
            db.execute(text(f"GRANT USAGE ON SCHEMA seguridad TO {user.username}"))
            db.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA seguridad TO {user.username}"))
            db.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA seguridad TO {user.username}"))
        except Exception:
            pass

    db.commit()
    db.refresh(new_user)
    return new_user

@router.put("/users/{id_usuario}", response_model=schemas.Usuario)
async def update_user(id_usuario: int, user_update: schemas.UsuarioUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Actualizar un usuario existente de forma parcial y sincronizar cambios en PostgreSQL.
    """
    db_user = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    old_username = db_user.username
    current_username = old_username
    
    # Si se actualiza el nombre de usuario
    if user_update.username is not None and user_update.username != db_user.username:
        if not re.match(r"^[a-zA-Z0-9_]+$", user_update.username):
            raise HTTPException(
                status_code=400, 
                detail="El nombre de usuario solo puede contener letras, números y guiones bajos"
            )
            
        existing_user = db.query(Usuario).filter(Usuario.username == user_update.username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya está registrado")
            
        # Intentar renombrar usuario en PostgreSQL
        try:
            db.execute(text(f"ALTER USER {old_username} RENAME TO {user_update.username}"))
        except Exception:
            pass
            
        db_user.username = user_update.username
        current_username = user_update.username
        
    # Si se actualiza el rol
    if user_update.id_rol is not None:
        db_role = db.query(Rol).filter(Rol.id_rol == user_update.id_rol).first()
        if not db_role:
            raise HTTPException(status_code=400, detail="El rol especificado no existe")
        db_user.id_rol = user_update.id_rol
        
    # Si se actualiza la contraseña
    if user_update.password is not None:
        db_user.password_hash = security.get_password_hash(user_update.password)
        try:
            db.execute(text(f"ALTER USER {current_username} WITH PASSWORD :password"), {"password": user_update.password})
        except Exception:
            pass
        
    # Si se actualiza el estado activo
    if user_update.activo is not None:
        db_user.activo = user_update.activo
        login_clause = "LOGIN" if user_update.activo else "NOLOGIN"
        try:
            db.execute(text(f"ALTER USER {current_username} {login_clause}"))
        except Exception:
            pass

    # Si se actualiza la empresa
    if current_user.rol and current_user.rol.nombre.lower() == "superadmin":
        if hasattr(user_update, "id_empresa") and user_update.id_empresa is not None:
            db_user.id_empresa = user_update.id_empresa
        # si envían explícitamente id_empresa como nulo, podríamos permitir limpiar la empresa
        # pero BaseModel exclude_unset en algunos casos no envía None, lo omitimos si no es None
        # si queremos que superadmin limpie la empresa, lo podemos forzar si id_empresa == "" o -1
        # por ahora, si envía id_empresa, se lo asignamos
        if "id_empresa" in user_update.model_dump(exclude_unset=True):
            db_user.id_empresa = user_update.id_empresa
        
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{id_usuario}", status_code=status.HTTP_200_OK)
async def delete_user(id_usuario: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    """
    Eliminar un usuario y borrar su cuenta de PostgreSQL asociada.
    """
    db_user = db.query(Usuario).filter(Usuario.id_usuario == id_usuario).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    username_to_delete = db_user.username
    
    # Eliminar de la base de datos de la app
    db.delete(db_user)
    db.commit()
    
    # Eliminar usuario de PostgreSQL y transferir propiedad de sus objetos para evitar bloqueos
    try:
        db.execute(text(f"REASSIGN OWNED BY {username_to_delete} TO postgres"))
        db.execute(text(f"DROP OWNED BY {username_to_delete}"))
        db.execute(text(f"DROP USER IF EXISTS {username_to_delete}"))
        db.commit()
    except Exception:
        pass
        
    return {"detail": "Usuario eliminado correctamente"}
