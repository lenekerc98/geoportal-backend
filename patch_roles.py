from app.core.database import engine, SessionLocal
from sqlalchemy import text
import json

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE seguridad.roles ADD COLUMN IF NOT EXISTS permisos JSONB DEFAULT '{}'::jsonb;"))
    conn.commit()

db = SessionLocal()

permisos_superadmin = json.dumps({
    "geoportal": True,
    "edicion_predios": True,
    "gestion_datos": True,
    "catastro_4d": True,
    "gestion_usuarios": True,
    "gestion_empresas": True,
    "qgis_sync": True
})

permisos_admin = json.dumps({
    "geoportal": True,
    "edicion_predios": True,
    "gestion_datos": True,
    "catastro_4d": True,
    "gestion_usuarios": True,
    "gestion_empresas": False,
    "qgis_sync": True
})

permisos_usuario = json.dumps({
    "geoportal": True,
    "edicion_predios": True,
    "gestion_datos": False,
    "catastro_4d": True,
    "gestion_usuarios": False,
    "gestion_empresas": False,
    "qgis_sync": False
})

db.execute(text("UPDATE seguridad.roles SET permisos = :p WHERE LOWER(nombre) IN ('superadmin', 'superadministrador')"), {"p": permisos_superadmin})
db.execute(text("UPDATE seguridad.roles SET permisos = :p WHERE LOWER(nombre) = 'admin'"), {"p": permisos_admin})
db.execute(text("UPDATE seguridad.roles SET permisos = :p WHERE LOWER(nombre) = 'usuario'"), {"p": permisos_usuario})
db.commit()
print("Roles updated successfully!")
