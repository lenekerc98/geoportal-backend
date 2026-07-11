import os
import re
from osgeo import gdal, osr
import psycopg2

def cargar_env_manualmente(ruta_env):
    """Carga las variables del archivo .env al entorno de ejecución manualmente."""
    if not os.path.exists(ruta_env):
        return
    with open(ruta_env, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Ignorar comentarios o líneas vacías
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                parts = line.split('=', 1)
                key = parts[0].strip()
                val = parts[1].strip()
                # Quitar comillas si las hay
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                os.environ[key] = val

# Obtener directorio actual
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
# Cargar archivo .env
cargar_env_manualmente(os.path.join(BACKEND_DIR, '.env'))

DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:L3n3k3rx98.@127.0.0.1:5432/catastro_db")
DIR_ORTOFOTOS = r"D:\Ortofotos_unificado"
VRT_FILE = os.path.join(BACKEND_DIR, "ortofotos.vrt")
SRID_DESTINO = 32717  # UTM 17S (Catastro 2026)

def parse_db_url(url):
    """Parsea una URL de conexión de postgresql a parámetros para psycopg2."""
    pattern = r"postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)"
    m = re.match(pattern, url)
    if not m:
        raise ValueError("DATABASE_URL no tiene un formato válido")
    user, password, host, port, dbname = m.groups()
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port or 5432,
        "dbname": dbname
    }

def obtener_datos_ortofoto(ruta_archivo):
    """Usa GDAL para obtener los límites de la imagen y su SRID."""
    gdal.UseExceptions()
    try:
        ds = gdal.Open(ruta_archivo)
        width = ds.RasterXSize
        height = ds.RasterYSize
        gt = ds.GetGeoTransform()
        
        xmin = gt[0]
        ymax = gt[3]
        xmax = xmin + width * gt[1] + height * gt[2]
        ymin = ymax + width * gt[4] + height * gt[5]
        
        proj = ds.GetProjection()
        srs = osr.SpatialReference()
        srs.ImportFromWkt(proj)
        
        srs.AutoIdentifyEPSG()
        epsg_code = srs.GetAuthorityCode(None)
        srid = int(epsg_code) if epsg_code else None
        
        wkt_geom = f"POLYGON(({xmin} {ymin}, {xmin} {ymax}, {xmax} {ymax}, {xmax} {ymin}, {xmin} {ymin}))"
        
        return wkt_geom, srid
    except Exception as e:
        print(f"Error al leer metadatos de {os.path.basename(ruta_archivo)}: {e}")
        return None, None

def catalogar():
    if not os.path.exists(DIR_ORTOFOTOS):
        print(f"Error: La ruta de las ortofotos no existe: {DIR_ORTOFOTOS}")
        return
        
    print(f"1. Escaneando ortofotos en: {DIR_ORTOFOTOS}...")
    archivos = [f for f in os.listdir(DIR_ORTOFOTOS) if f.lower().endswith(('.tif', '.tiff', '.ecw', '.jp2'))]
    print(f"Se encontraron {len(archivos)} archivos ráster compatibles.")
    
    if not archivos:
        print("No hay archivos ráster para procesar. Cancelando.")
        return
        
    # --- 1. Crear el mosaico virtual VRT ---
    print(f"\n2. Generando Mosaico Virtual (VRT) en: {VRT_FILE}...")
    rutas_completas = [os.path.join(DIR_ORTOFOTOS, f) for f in archivos]
    try:
        gdal.UseExceptions()
        # VRT nativo (sin forzar transparencia, permite ver 1:1 sin desaparecer)
        vrt_ds = gdal.BuildVRT(VRT_FILE, rutas_completas)
        
        # Construir pirámides automáticamente para navegación rápida (Google Maps)
        print("\n3. Construyendo pirámides externas (.vrt.ovr)... (Esto tomará de 10 a 30 minutos)")
        print("Progreso general de las pirámides:")
        # Barra de progreso nativa en terminal
        vrt_ds.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64], callback=gdal.TermProgress_nocb)
        
        vrt_ds = None  # Cierra y guarda
        print("\nMosaico VRT y pirámides guardados con éxito.")
    except Exception as vrt_err:
        print(f"\nError al generar el Mosaico VRT o pirámides: {vrt_err}")
        return

    # --- 2. Catalogar en PostgreSQL ---
    print("\n4. Conectando a PostgreSQL...")
    db_config = parse_db_url(DB_URL)
    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()
    
    try:
        # Crear la tabla de catálogo si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catastro.ortofotos_catalogo (
                id SERIAL PRIMARY KEY,
                nombre_archivo VARCHAR(255) UNIQUE NOT NULL,
                ruta_completa VARCHAR(1024) NOT NULL,
                srid_original INT,
                tipo_archivo VARCHAR(10),
                geom geometry(Polygon, 32717)
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ortofotos_catalogo_geom ON catastro.ortofotos_catalogo USING gist(geom);")
        conn.commit()
        
        insertados = 0
        actualizados = 0
        
        print("\n5. Guardando límites y rutas en PostgreSQL...")
        for i, f in enumerate(archivos, 1):
            print(f"[{i}/{len(archivos)}] Registrando en BD: {f} ...")
            
            ruta_completa = os.path.join(DIR_ORTOFOTOS, f)
            wkt_geom, srid_orig = obtener_datos_ortofoto(ruta_completa)
            
            if not wkt_geom:
                continue
                
            srid_lectura = srid_orig if srid_orig else SRID_DESTINO
            
            try:
                cursor.execute(
                    "SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = %s", 
                    (f,)
                )
                exists = cursor.fetchone()
                
                tipo = f.split('.')[-1].lower() if '.' in f else 'desconocido'
                if exists:
                    cursor.execute("""
                        UPDATE catastro.ortofotos_catalogo
                        SET ruta_completa = %s,
                            srid_original = %s,
                            tipo_archivo = %s,
                            geom = ST_Transform(ST_GeomFromText(%s, %s), %s)
                        WHERE nombre_archivo = %s
                    """, (ruta_completa, srid_orig, tipo, wkt_geom, srid_lectura, SRID_DESTINO, f))
                    actualizados += 1
                else:
                    cursor.execute("""
                        INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, tipo_archivo, geom)
                        VALUES (%s, %s, %s, %s, ST_Transform(ST_GeomFromText(%s, %s), %s))
                    """, (f, ruta_completa, srid_orig, tipo, wkt_geom, srid_lectura, SRID_DESTINO))
                    insertados += 1
            except Exception as insert_err:
                print(f"  -> Error al registrar en BD {f}: {insert_err}")
                conn.rollback()
                continue
        
        print("\n6. Registrando el Mosaico VRT Maestro en la BD...")
        wkt_geom_vrt, srid_vrt = obtener_datos_ortofoto(VRT_FILE)
        if wkt_geom_vrt:
            cursor.execute("SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = 'ortofotos.vrt'")
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE catastro.ortofotos_catalogo SET ruta_completa = %s, srid_original = %s, tipo_archivo = 'vrt', geom = ST_Transform(ST_GeomFromText(%s, %s), %s) WHERE nombre_archivo = 'ortofotos.vrt'
                """, (VRT_FILE, srid_vrt, wkt_geom_vrt, srid_vrt or SRID_DESTINO, SRID_DESTINO))
            else:
                cursor.execute("""
                    INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, tipo_archivo, geom)
                    VALUES ('ortofotos.vrt', %s, %s, 'vrt', ST_Transform(ST_GeomFromText(%s, %s), %s))
                """, (VRT_FILE, srid_vrt, wkt_geom_vrt, srid_vrt or SRID_DESTINO, SRID_DESTINO))
            print("VRT Maestro catalogado exitosamente.")

        conn.commit()
        print("\n--- PROCESO COMPLETADO CON ÉXITO ---")
        print(f"Ortofotos insertadas en DB: {insertados}")
        print(f"Ortofotos actualizadas en DB: {actualizados}")
        print(f"Mosaico VRT limpio listo para QGIS en: {VRT_FILE}")
        
    except Exception as e:
        print(f"\nError general en el proceso de BD: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    catalogar()
