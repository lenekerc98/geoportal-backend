import os
import logging
from typing import Optional
from fastapi import Request
from jose import jwt
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import CreateSchema
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)

# Base de Producción (AWS RDS default)
DATABASE_URL_PROD = os.getenv("DATABASE_URL_PROD") or os.getenv("DATABASE_URL")
# Base de Pruebas (AWS RDS Sandbox)
DATABASE_URL_TEST = os.getenv("DATABASE_URL_TEST")

engine_prod = create_engine(
    DATABASE_URL_PROD,
    pool_size=20,
    max_overflow=50,
    pool_timeout=60.0,
    pool_pre_ping=True
)
SessionProd = sessionmaker(autocommit=False, autoflush=False, bind=engine_prod)

if DATABASE_URL_TEST:
    engine_test = create_engine(
        DATABASE_URL_TEST,
        pool_size=10,
        max_overflow=20,
        pool_timeout=60.0,
        pool_pre_ping=True
    )
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)
else:
    engine_test = engine_prod
    SessionTest = SessionProd

# Compatibilidad con código existente
engine = engine_prod
SessionLocal = SessionProd

Base = declarative_base()

# Asegurar que el esquema "seguridad" exista antes de crear tablas
event.listen(Base.metadata, 'before_create', CreateSchema('seguridad', if_not_exists=True))

def is_superadmin_request(request: Optional[Request]) -> bool:
    if not request:
        return False
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    token = auth_header[7:].strip()
    try:
        from app.core.security import SECRET_KEY, ALGORITHM
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        role = str(payload.get("role") or "").lower().strip()
        return role in ["superadmin", "superadministrador"]
    except Exception:
        return False

def get_db(request: Request = None):
    """
    Rutas dinámicas por solicitud:
    - Si el encabezado 'X-Database-Env' es 'test' Y el usuario tiene rol Superadmin:
      conecta a 'catastro-db-test' (AWS RDS).
    - Para cualquier otro caso (usuarios normales, operadores, o superadmin en modo prod):
      conecta siempre a 'catastro-db' (Producción AWS RDS).
    """
    use_test = False
    if request is not None:
        try:
            db_header = (request.headers.get("X-Database-Env") or request.headers.get("x-database-env") or "").strip().lower()
            if db_header == "test" and is_superadmin_request(request):
                use_test = True
        except Exception as e:
            logger.warning(f"Error checking db routing header: {e}")

    if use_test:
        db = SessionTest()
    else:
        db = SessionProd()

    try:
        yield db
    finally:
        db.close()
