import os
import sys
import logging
from sqlalchemy import text
from osgeo import gdal

logger = logging.getLogger(__name__)

def configure_gdal():
    """Configura las variables de entorno y opciones de GDAL."""
    proj_lib = os.getenv('PROJ_LIB')
    if not proj_lib and sys.platform == "win32":
        proj_lib = r"C:\Program Files\QGIS 4.0.2\share\proj"
        os.environ['PROJ_LIB'] = proj_lib

    if proj_lib:
        gdal.SetConfigOption('PROJ_LIB', proj_lib)

    # Opciones de rendimiento y memoria para GDAL
    gdal.SetConfigOption('GDAL_CACHEMAX', '256')
    gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
    gdal.SetConfigOption('VSI_CACHE', 'TRUE')


def init_db_schema(engine):
    """
    Inicializa extensiones espaciales, esquemas, tablas base,
    índices y vistas requeridas por el sistema catastral.
    """
    with engine.connect() as connection:
        try:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            has_postgis = True
        except Exception:
            has_postgis = False
            logger.warning("La extensión PostGIS no está disponible en este servidor de PostgreSQL.")

        if has_postgis:
            try:
                connection.execute(text("CREATE SCHEMA IF NOT EXISTS catastro"))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.proyecto (
                        id SERIAL PRIMARY KEY,
                        nombre VARCHAR(255) NOT NULL,
                        descripcion TEXT,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.capas_adicionales (
                        id SERIAL PRIMARY KEY,
                        nombre_capa VARCHAR(255) NOT NULL,
                        tabla_db VARCHAR(100) NOT NULL,
                        tipo_geometria VARCHAR(50),
                        empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                        fecha_subida TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.empresa (
                        id SERIAL PRIMARY KEY,
                        ruc VARCHAR(20) UNIQUE,
                        nombre VARCHAR(255) NOT NULL,
                        telefono VARCHAR(50),
                        correo VARCHAR(100),
                        direccion TEXT,
                        parametros JSONB DEFAULT '{}'::jsonb,
                        proyecto_id INT REFERENCES catastro.proyecto(id) ON DELETE SET NULL,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS proyecto_id INT REFERENCES catastro.proyecto(id) ON DELETE SET NULL"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS telefono VARCHAR(50)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS correo VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS direccion TEXT"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS provincia VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS canton VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS ciudad VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS sector VARCHAR(50)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500)"))
                connection.execute(text("ALTER TABLE catastro.empresa ADD COLUMN IF NOT EXISTS bandera_url VARCHAR(500)"))
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
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS creado_por INT REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS modificado_por INT REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS fecha_modificacion TIMESTAMP"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS angulo_texto FLOAT DEFAULT 0.0"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS codigo_carta VARCHAR(50)"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS nombre_carta VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS cuadricula_carta VARCHAR(50)"))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.cartas_topograficas (
                        id SERIAL PRIMARY KEY,
                        codigo VARCHAR(50) NOT NULL,
                        nombre VARCHAR(100) NOT NULL,
                        cuadricula VARCHAR(50) DEFAULT 'ZONA 17S',
                        escala VARCHAR(20) DEFAULT '1:50000',
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.predio_historial (
                        id SERIAL PRIMARY KEY,
                        predio_id INT REFERENCES catastro.predio(id) ON DELETE CASCADE,
                        area_ha NUMERIC(14, 4),
                        geom geometry(Polygon, 32717),
                        modificado_por INT REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL,
                        observacion TEXT,
                        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.capa_dibujo (
                        id SERIAL PRIMARY KEY,
                        tipo VARCHAR(50) NOT NULL,
                        geom geometry(Geometry, 32717),
                        usuario_id INT REFERENCES seguridad.usuarios(id_usuario) ON DELETE SET NULL,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS catastro.tecnico (
                        id SERIAL PRIMARY KEY,
                        nombre VARCHAR(255) NOT NULL,
                        cargo VARCHAR(150),
                        registro_senescyt VARCHAR(100),
                        empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                        activo BOOLEAN DEFAULT TRUE,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))

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
                
                # Columnas históricas y de Fase 1 (sector y parroquia)
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Activo'"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS predio_padre_id INT REFERENCES catastro.predio(id)"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE SET NULL"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS proyecto_id INT REFERENCES catastro.proyecto(id) ON DELETE SET NULL"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS sector VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS parroquia VARCHAR(100)"))
                connection.execute(text("ALTER TABLE catastro.capas_adicionales ADD COLUMN IF NOT EXISTS tipo_capa VARCHAR(50) DEFAULT 'adicional'"))
                connection.execute(text("ALTER TABLE catastro.capas_adicionales ADD COLUMN IF NOT EXISTS color VARCHAR(20) DEFAULT '#a855f7'"))
                connection.execute(text("ALTER TABLE catastro.capas_adicionales ADD COLUMN IF NOT EXISTS opacidad NUMERIC(3,2) DEFAULT 0.35"))
                connection.execute(text("ALTER TABLE catastro.capas_adicionales ADD COLUMN IF NOT EXISTS borde_color VARCHAR(20) DEFAULT '#7e22ce'"))
                connection.execute(text("ALTER TABLE catastro.capas_adicionales ADD COLUMN IF NOT EXISTS borde_grosor INT DEFAULT 2"))
                connection.execute(text("ALTER TABLE catastro.cantones ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 32717)"))
                connection.execute(text("ALTER TABLE catastro.ciudades ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 32717)"))
                connection.execute(text("INSERT INTO catastro.ciudades (nombre, codigo_dpa, id_canton) VALUES ('Pijullo', '120652', 127) ON CONFLICT (codigo_dpa) DO UPDATE SET nombre = 'Pijullo', id_canton = 127"))
                
                connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Activo'"))
                connection.execute(text("ALTER TABLE catastro.vertice ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP"))
                
                connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Activo'"))
                connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS fecha_baja TIMESTAMP"))
                connection.execute(text("ALTER TABLE catastro.linea_lindero ADD COLUMN IF NOT EXISTS tramo VARCHAR(100)"))

                try:
                    connection.execute(text("ALTER TABLE catastro.ortofotos_catalogo ADD COLUMN IF NOT EXISTS empresa_id INT REFERENCES catastro.empresa(id) ON DELETE SET NULL"))
                    connection.execute(text("ALTER TABLE catastro.ortofotos_catalogo ADD COLUMN IF NOT EXISTS proyecto_id INT REFERENCES catastro.proyecto(id) ON DELETE SET NULL"))
                    connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS codigo_anterior VARCHAR(100)"))
                    connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS nombre_predio VARCHAR(255)"))
                    connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS texto_interno TEXT"))
                    connection.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS textos_internos_json JSONB DEFAULT '[]'::jsonb"))
                except Exception:
                    pass

                connection.execute(text("DROP VIEW IF EXISTS catastro.v_predio_completo CASCADE"))
                connection.execute(text("""
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
                        p.sector,
                        p.parroquia,
                        pos.cedula,
                        pos.nombre AS nombre_posesionario,
                        p.codigo_carta,
                        p.nombre_carta,
                        p.cuadricula_carta,
                        p.codigo_anterior,
                        p.nombre_predio,
                        p.texto_interno,
                        p.textos_internos_json
                    FROM catastro.predio p
                    LEFT JOIN catastro.posesionario pos ON p.posesionario_id = pos.id
                """))
                connection.commit()
                
                # Actualizar esquema de seguridad
                try:
                    connection.execute(text("ALTER TABLE seguridad.usuarios ADD COLUMN IF NOT EXISTS id_empresa INT REFERENCES catastro.empresa(id) ON DELETE SET NULL"))
                    connection.commit()
                except Exception:
                    connection.rollback()
                    
            except Exception as e:
                connection.rollback()
                logger.error(f"Error al inicializar las tablas de catastro: {e}")

            # Claves foráneas seguras
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

            # Índices de rendimiento para consultas GIS y CAD
            for idx_stmt in [
                "CREATE INDEX IF NOT EXISTS idx_cad_archivo_capa ON catastro.capas_cad_cartas (nombre_archivo, capa_cad)",
                "CREATE INDEX IF NOT EXISTS idx_cad_tipo_geom ON catastro.capas_cad_cartas (tipo_geometria)",
                "CREATE INDEX IF NOT EXISTS idx_predio_estado ON catastro.predio (estado)",
                "CREATE INDEX IF NOT EXISTS idx_predio_fecha_baja ON catastro.predio (fecha_baja)",
                "CREATE INDEX IF NOT EXISTS idx_predio_fecha_creacion ON catastro.predio (fecha_creacion)",
                "CREATE INDEX IF NOT EXISTS idx_vertice_empresa_id ON catastro.vertice (empresa_id)",
                "CREATE INDEX IF NOT EXISTS idx_vertice_cod_catastral ON catastro.vertice (cod_catastral)",
                "CREATE INDEX IF NOT EXISTS idx_vertice_estado ON catastro.vertice (estado)",
                "CREATE INDEX IF NOT EXISTS idx_vertice_fecha_baja ON catastro.vertice (fecha_baja)",
                "CREATE INDEX IF NOT EXISTS idx_linea_lindero_empresa_id ON catastro.linea_lindero (empresa_id)",
                "CREATE INDEX IF NOT EXISTS idx_linea_lindero_cod_catastral ON catastro.linea_lindero (cod_catastral)",
                "CREATE INDEX IF NOT EXISTS idx_linea_lindero_estado ON catastro.linea_lindero (estado)",
                "CREATE INDEX IF NOT EXISTS idx_linea_lindero_fecha_baja ON catastro.linea_lindero (fecha_baja)",
                "CREATE INDEX IF NOT EXISTS idx_cartas_topograficas_codigo ON catastro.cartas_topograficas (codigo)",
                "CREATE INDEX IF NOT EXISTS idx_cartas_topograficas_nombre_archivo ON catastro.cartas_topograficas (nombre_archivo)"
            ]:
                try:
                    connection.execute(text(idx_stmt))
                    connection.commit()
                except Exception:
                    connection.rollback()

            # Permisos de esquema para roles de base de datos
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
                
            # Creación del esquema de seguridad si no existe
            try:
                connection.execute(text("CREATE SCHEMA IF NOT EXISTS seguridad"))
                connection.commit()
            except Exception:
                connection.rollback()

            # Creación del esquema de interoperabilidad para datos externos (SQL Server)
            try:
                connection.execute(text("CREATE SCHEMA IF NOT EXISTS interoperabilidad"))
                connection.execute(text("""
                    CREATE TABLE IF NOT EXISTS interoperabilidad.referencias_prediales (
                        id SERIAL PRIMARY KEY,
                        cod_catastral VARCHAR(100),
                        id_titular VARCHAR(50),
                        propietario VARCHAR(255),
                        nombre_predio VARCHAR(255),
                        sitio VARCHAR(100),
                        rcx NUMERIC(14, 4),
                        rcy NUMERIC(14, 4),
                        area_ref VARCHAR(50),
                        geom geometry(Point, 32717),
                        geom_4326 geometry(Point, 4326),
                        fecha_sincronizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        activo BOOLEAN DEFAULT TRUE,
                        CONSTRAINT uq_ref_cod_rc UNIQUE (cod_catastral, rcx, rcy)
                    );
                """))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_pred_cod ON interoperabilidad.referencias_prediales(cod_catastral)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_pred_titular ON interoperabilidad.referencias_prediales(id_titular)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_pred_geom ON interoperabilidad.referencias_prediales USING GIST(geom)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_ref_pred_geom4326 ON interoperabilidad.referencias_prediales USING GIST(geom_4326)"))
                connection.commit()
            except Exception:
                connection.rollback()


