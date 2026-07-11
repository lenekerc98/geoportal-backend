import os
import re
import threading
from osgeo import gdal, osr
import psycopg2
from sqlalchemy.orm import Session
from sqlalchemy import text, create_engine
from app.core.ortofoto_service import PROGRESS_STORE
from app.core.logger import log_audit

# Obtener directorio actual
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR_ORTOFOTOS = os.getenv("DIR_ORTOFOTOS_ORIGINALES", r"C:\LNCZ\proyecto-catastro-2026\Ortofotos")
VRT_FILE = os.path.join(BACKEND_DIR, "ortofotos.vrt")
SRID_DESTINO = 32717  # UTM 17S (Catastro 2026)

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

def run_catalogacion_masiva(db: Session, empresa_id: int):
    task_id = str(uuid.uuid4())
    PROGRESS_STORE[task_id] = {"progress": 0, "status": "Iniciando...", "error": False}
    
    # Pasamos la URL de la base de datos y la empresa para que el hilo pueda crear su propia conexión
    db_url = str(db.get_bind().url)
    hilo = threading.Thread(target=_run_catalogacion_masiva, args=(task_id, db_url, empresa_id))
    hilo.start()
    return task_id

def _run_catalogacion_masiva(task_id: str, db_url: str, empresa_id: int):
    PROGRESS_STORE[task_id] = {"progress": 5, "status": "Iniciando escaneo de carpeta..."}
    
    # Session for logging
    engine = create_engine(db_url)
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    if not os.path.exists(DIR_ORTOFOTOS):
        PROGRESS_STORE[task_id] = {"progress": 100, "status": f"Error: La ruta no existe {DIR_ORTOFOTOS}", "error": True}
        log_audit(db, "ERROR", "CATALOGACION_MASIVA_FALLO", f"La ruta de ortofotos no existe: {DIR_ORTOFOTOS}")
        db.close()
        return
        
    archivos = [f for f in os.listdir(DIR_ORTOFOTOS) if f.lower().endswith(('.tif', '.tiff', '.ecw', '.jp2'))]
    
    if not archivos:
        PROGRESS_STORE[task_id] = {"progress": 100, "status": "Error: No hay archivos ráster para procesar.", "error": True}
        log_audit(db, "WARNING", "CATALOGACION_MASIVA_VACIA", "No se encontraron archivos en la carpeta de ortofotos.")
        db.close()
        return
        
    PROGRESS_STORE[task_id] = {"progress": 15, "status": f"Generando Mosaico Virtual (VRT) para {len(archivos)} ortofotos..."}
    log_audit(db, "INFO", "CATALOGACION_MASIVA_INICIO", f"Iniciando catalogación masiva de {len(archivos)} ortofotos.")
    
    rutas_completas = [os.path.join(DIR_ORTOFOTOS, f) for f in archivos]
    try:
        gdal.UseExceptions()
        vrt_ds = gdal.BuildVRT(VRT_FILE, rutas_completas)
        
        def callback(complete, message, cb_data):
            # progress de GDAL va de 0.0 a 1.0. 
            # Las pirámides toman desde el 30% hasta el 80% de nuestra barra de progreso.
            p = 30 + int(complete * 50)
            if task_id in PROGRESS_STORE:
                PROGRESS_STORE[task_id]["progress"] = p
                PROGRESS_STORE[task_id]["status"] = f"Construyendo pirámides... {int(complete*100)}%"
            return 1

        vrt_ds.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64], callback=callback)
        vrt_ds = None
    except Exception as vrt_err:
        PROGRESS_STORE[task_id] = {"progress": 100, "status": f"Error en VRT: {str(vrt_err)}", "error": True}
        log_audit(db, "ERROR", "CATALOGACION_MASIVA_FALLO", f"Error generando VRT: {str(vrt_err)}")
        db.close()
        return

    PROGRESS_STORE[task_id] = {"progress": 85, "status": "Conectando a PostgreSQL para catalogar metadatos..."}
    
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS catastro.ortofotos_catalogo (
                id SERIAL PRIMARY KEY,
                nombre_archivo VARCHAR(255) UNIQUE NOT NULL,
                ruta_completa VARCHAR(1024) NOT NULL,
                srid_original INT,
                tipo_archivo VARCHAR(10),
                geom geometry(Polygon, 32717),
                empresa_id INT REFERENCES catastro.empresa(id) ON DELETE CASCADE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ortofotos_catalogo_geom ON catastro.ortofotos_catalogo USING gist(geom);")
        conn.commit()
        
        for i, f in enumerate(archivos, 1):
            ruta_completa = os.path.join(DIR_ORTOFOTOS, f)
            wkt_geom, srid_orig = obtener_datos_ortofoto(ruta_completa)
            
            if not wkt_geom:
                continue
                
            srid_lectura = srid_orig if srid_orig else SRID_DESTINO
            
            cursor.execute(
                "SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = %s", 
                (f,)
            )
            existe = cursor.fetchone()
            
            if existe:
                cursor.execute("""
                    UPDATE catastro.ortofotos_catalogo
                    SET ruta_completa = %s, srid_original = %s, 
                        geom = ST_Transform(ST_GeomFromText(%s, %s), %s),
                        empresa_id = %s
                    WHERE nombre_archivo = %s
                """, (ruta_completa, srid_orig, wkt_geom, srid_lectura, SRID_DESTINO, empresa_id, f))
            else:
                cursor.execute("""
                    INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, tipo_archivo, geom, empresa_id)
                    VALUES (%s, %s, %s, 'TIFF', ST_Transform(ST_GeomFromText(%s, %s), %s), %s)
                """, (f, ruta_completa, srid_orig, wkt_geom, srid_lectura, SRID_DESTINO, empresa_id))
        
        # Registrar el VRT
        wkt_vrt, _ = obtener_datos_ortofoto(VRT_FILE)
        if wkt_vrt:
            cursor.execute("SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = 'ortofotos.vrt'")
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE catastro.ortofotos_catalogo
                    SET ruta_completa = %s, srid_original = %s, 
                        geom = ST_GeomFromText(%s, %s),
                        empresa_id = %s
                    WHERE nombre_archivo = 'ortofotos.vrt'
                """, (VRT_FILE, SRID_DESTINO, wkt_vrt, SRID_DESTINO, empresa_id))
            else:
                cursor.execute("""
                    INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, tipo_archivo, geom, empresa_id)
                    VALUES ('ortofotos.vrt', %s, %s, 'VRT', ST_GeomFromText(%s, %s), %s)
                """, (VRT_FILE, SRID_DESTINO, wkt_vrt, SRID_DESTINO, empresa_id))
                
        conn.commit()
        cursor.close()
        conn.close()
        
        PROGRESS_STORE[task_id] = {"progress": 100, "status": "Catalogación Masiva completada con éxito."}
        log_audit(db, "INFO", "CATALOGACION_MASIVA_EXITO", f"Catalogación masiva finalizada. Se procesaron {len(archivos)} ortofotos.")
    except Exception as e:
        PROGRESS_STORE[task_id] = {"progress": 100, "status": f"Error en BD: {str(e)}", "error": True}
        log_audit(db, "ERROR", "CATALOGACION_MASIVA_FALLO", f"Error en base de datos: {str(e)}")
    finally:
        db.close()
