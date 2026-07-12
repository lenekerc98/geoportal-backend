import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.database import engine, Base
from app.routers import auth, users, gis, system, empresas
from osgeo import gdal

import sys
proj_lib = os.getenv('PROJ_LIB')
if not proj_lib and sys.platform == "win32":
    proj_lib = r"C:\Program Files\QGIS 4.0.2\share\proj"
    os.environ['PROJ_LIB'] = proj_lib

if proj_lib:
    gdal.SetConfigOption('PROJ_LIB', proj_lib)

# Optimizaciones de rendimiento extremo para GDAL
gdal.SetConfigOption('GDAL_CACHEMAX', '2048') # 2GB de RAM para GDAL
gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
gdal.SetConfigOption('VSI_CACHE', 'TRUE')
with engine.connect() as connection:
    try:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        has_postgis = True
    except Exception as pg_err:
        has_postgis = False
        print("ADVERTENCIA: La extensión PostGIS no está disponible en este servidor de PostgreSQL.")
        print("Para habilitar la funcionalidad GIS y la integración con QGIS, por favor instala PostGIS en tu servidor.")
        
    if has_postgis:
        try:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS catastro"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.empresa (
                    id SERIAL PRIMARY KEY,
                    ruc VARCHAR(20) UNIQUE,
                    nombre VARCHAR(255) NOT NULL,
                    telefono VARCHAR(50),
                    correo VARCHAR(100),
                    direccion TEXT,
                    parametros JSONB DEFAULT '{}'::jsonb,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS telefono VARCHAR(50)"))
            connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS correo VARCHAR(100)"))
            connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS direccion TEXT"))
            connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS parametros JSONB DEFAULT '{}'::jsonb"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.posesionario (
                    id SERIAL PRIMARY KEY,
                    cedula VARCHAR(50) UNIQUE NOT NULL,
                    nombre VARCHAR(255) NOT NULL,
                    empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.posesionario ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE"))
            connection.execute(text("ALTER TABLE catastro.posesionario ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.codigo_catastral (
                    codigo VARCHAR(100) PRIMARY KEY,
                    posesionario_id INT REFERENCES catastro.posesionario(id) ON DELETE SET NULL,
                    empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                    activo BOOLEAN DEFAULT TRUE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.codigo_catastral ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.predio (
                    id SERIAL PRIMARY KEY,
                    cod_catastral VARCHAR(100) UNIQUE REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE,
                    posesionario_id INT REFERENCES catastro.posesionario(id) ON DELETE SET NULL,
                    empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                    area_ha NUMERIC(14, 4),
                    geom geometry(Polygon, 32717),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE"))
            connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.vertice (
                    id SERIAL PRIMARY KEY,
                    predio_id INT REFERENCES catastro.predio(id) ON DELETE CASCADE,
                    cod_catastral VARCHAR(100) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE,
                    empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                    codigo VARCHAR(50) NOT NULL,
                    coord_x NUMERIC(14, 4),
                    coord_y NUMERIC(14, 4),
                    geom geometry(Point, 32717),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS coord_x NUMERIC(14, 4)"))
            connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS coord_y NUMERIC(14, 4)"))
            connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS cod_catastral VARCHAR(100)"))
            connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE"))
            connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS catastro.linea_lindero (
                    id SERIAL PRIMARY KEY,
                    predio_id INT REFERENCES catastro.predio(id) ON DELETE CASCADE,
                    cod_catastral VARCHAR(100) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE,
                    empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                    longitud NUMERIC(14, 2),
                    rumbo VARCHAR(100),
                    colindante VARCHAR(255),
                    geom geometry(LineString, 32717),
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS cod_catastral VARCHAR(100)"))
            connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE"))
            connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            connection.execute(text("ALTER TABLE catastro.codigo_catastral ADD COLUMN IF NOT EXISTS posesionario_id INT"))
            connection.execute(text("DROP VIEW IF EXISTS catastro.v_predio_completo CASCADE"))
            connection.execute(text("""
                CREATE OR REPLACE VIEW catastro.v_predio_completo AS
                SELECT 
                    p.id,
                    p.cod_catastral,
                    p.posesionario_id,
                    p.empresa_id,
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
            connection.commit()
            
            # Actualizar también esquema de seguridad
            try:
                connection.execute(text("ALTER TABLE seguridad.usuarios ADD COLUMN IF NOT EXISTS id_empresa INT REFERENCES catastro.empresa(id) ON DELETE SET NULL"))
                connection.commit()
            except Exception as e_seg:
                connection.rollback()
                print(f"Error al actualizar seguridad.usuarios: {e_seg}")
                
            print("Esquema, tablas principales y vistas de catastro creados correctamente.")
        except Exception as e:
            connection.rollback()
            print(f"Error al inicializar las tablas principales de catastro: {e}")

        # Safe ALTER constraints run in separate clean sub-transactions
        for alter_stmt in [
            "ALTER TABLE catastro.codigo_catastral ADD CONSTRAINT codigo_catastral_posesionario_id_fkey FOREIGN KEY (posesionario_id) REFERENCES catastro.posesionario(id) ON DELETE SET NULL",
            "ALTER TABLE catastro.predio ADD CONSTRAINT predio_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE",
            "ALTER TABLE catastro.vertice ADD CONSTRAINT vertice_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE",
            "ALTER TABLE catastro.linea_lindero ADD CONSTRAINT linea_lindero_cod_catastral_fkey FOREIGN KEY (cod_catastral) REFERENCES catastro.codigo_catastral(codigo) ON DELETE CASCADE"
        ]:
            try:
                connection.execute(text(alter_stmt))
                connection.commit()
            except Exception:
                connection.rollback()

        # Grant permissions to user roles on catastro schema
        try:
            roles_result = connection.execute(text("SELECT rolname FROM pg_roles WHERE rolcanlogin = true"))
            roles = [row[0] for row in roles_result if not row[0].startswith("pg_") and row[0] != "postgres"]
            for user_role in roles:
                try:
                    connection.execute(text(f"GRANT USAGE ON SCHEMA catastro TO {user_role}"))
                    connection.execute(text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA catastro TO {user_role}"))
                    connection.execute(text(f"GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA catastro TO {user_role}"))
                    connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA catastro GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {user_role}"))
                    connection.execute(text(f"ALTER DEFAULT PRIVILEGES IN SCHEMA catastro GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {user_role}"))
                    connection.commit()
                except Exception:
                    connection.rollback()
        except Exception:
            connection.rollback()
            
        # Create seguridad schema for logs and users
        try:
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS seguridad"))
            connection.commit()
        except Exception:
            connection.rollback()

from app.models.user import Rol, Usuario
from app.models.log import Log

# Create DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Catastro API 2026")

# Leer orígenes permitidos desde el entorno o usar '*' por defecto
frontend_url_env = os.getenv("FRONTEND_URL", "*")

if frontend_url_env == "*":
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    origins = [url.strip() for url in frontend_url_env.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Geoportal API is running!"}

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(empresas.router, prefix="/api")
app.include_router(gis.router, prefix="/api")
app.include_router(system.router, prefix="/api")
