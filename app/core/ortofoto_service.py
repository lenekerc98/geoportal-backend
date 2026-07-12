import os
import time
import shutil
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
from osgeo import gdal, osr

from dotenv import load_dotenv

gdal.UseExceptions()
load_dotenv()

# Directorio donde se crearán los VRTs y OVRs
COMPLEMENTOS_DIR = os.getenv("DIR_ORTOFOTOS_COMPLEMENTOS", r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos")
ORTOFOTOS_DIR = os.getenv("DIR_ORTOFOTOS", r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Ortofotos")
os.makedirs(COMPLEMENTOS_DIR, exist_ok=True)
os.makedirs(ORTOFOTOS_DIR, exist_ok=True)
VRT_FILE = os.path.join(COMPLEMENTOS_DIR, "ortofotos.vrt")
SRID_DESTINO = 32717  # UTM 17S (Catastro 2026)

# Memoria global temporal para progreso de tareas
PROGRESS_STORE = {}

def gdal_progress_callback(complete, message, user_data):
    """Callback para que GDAL reporte el progreso."""
    task_id = user_data
    porcentaje = round(complete * 100, 2)
    PROGRESS_STORE[task_id] = porcentaje
    if porcentaje % 10 == 0:
        print(f"[GDAL Task {task_id}] Progreso: {porcentaje}%")
    return 1 # Devuelve 1 para continuar, 0 para abortar

def obtener_datos_ortofoto(ruta_archivo: str):
    """Usa GDAL para obtener los límites de la imagen y su SRID."""
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

def procesar_ortofoto_background(task_id: str, ruta_archivo: str, db: Session, dpa_data: dict = None):
    """
    Procesa la ortofoto en segundo plano de forma nativa para la nube (S3):
    - Lee la imagen desde S3 usando GDAL (/vsis3/...)
    - Crea un VRT temporal local para construir las pirámides (OVR).
    - Sube el VRT y OVR a S3 Complementos usando boto3.
    - Limpia los archivos temporales locales.
    - Guarda/actualiza la ruta S3 en PostgreSQL.
    """
    from app.core.file_utils import is_s3_path, get_s3_bucket_and_prefix
    import boto3
    
    PROGRESS_STORE[task_id] = 1.0
    print(f"[GIS Service] Iniciando procesamiento NUBE: {ruta_archivo}")
    
    nombre_archivo = os.path.basename(ruta_archivo)
    tipo_archivo = nombre_archivo.split('.')[-1].lower() if '.' in nombre_archivo else 'desconocido'
    
    # 1. Obtener datos geográficos del TIF directamente desde S3
    wkt_geom, srid_orig = obtener_datos_ortofoto(ruta_archivo)
    if not wkt_geom:
        print("[GIS Service] Error: No se pudo obtener la geometría.")
        PROGRESS_STORE[task_id] = -1
        return
        
    srid_lectura = srid_orig if srid_orig else SRID_DESTINO

    # Verificar si YA fue procesada
    q_check = text("SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :nombre")
    ya_existe = db.execute(q_check, {"nombre": nombre_archivo}).fetchone() is not None
    
    # 2. Construir VRT individual temporal y generarle pirámides
    if tipo_archivo in ['tif', 'tiff', 'ecw', 'jp2'] and not ya_existe:
        PROGRESS_STORE[task_id] = 10.0
        
        temp_dir = "/tmp/ortofotos_processing"
        os.makedirs(temp_dir, exist_ok=True)
        
        nombre_base = os.path.splitext(nombre_archivo)[0]
        vrt_local = os.path.join(temp_dir, f"{nombre_base}.vrt")
        ovr_local = vrt_local + ".ovr"
        
        try:
            print("[GIS Service] Creando VRT individual local temporal...")
            gdal.BuildVRT(vrt_local, [ruta_archivo])
            
            print("[GIS Service] Construyendo pirámides OVR...")
            ds_individual = gdal.Open(vrt_local, gdal.GA_Update)
            if ds_individual:
                ds_individual.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64], callback=gdal_progress_callback, callback_data=task_id)
                ds_individual = None
            else:
                print("[GIS Service] Advertencia: No se pudo abrir VRT local para pirámides.")
                
            PROGRESS_STORE[task_id] = 70.0
            
            # Subir VRT y OVR generados a S3
            comp_s3_url = os.getenv("DIR_ORTOFOTOS_COMPLEMENTOS")
            if comp_s3_url and is_s3_path(comp_s3_url):
                print(f"[GIS Service] Subiendo VRT y OVR a S3: {comp_s3_url}")
                s3 = boto3.client('s3')
                bucket, prefix = get_s3_bucket_and_prefix(comp_s3_url)
                
                vrt_key = f"{prefix}/{nombre_base}.vrt" if prefix else f"{nombre_base}.vrt"
                s3.upload_file(vrt_local, bucket, vrt_key)
                
                if os.path.exists(ovr_local):
                    ovr_key = f"{prefix}/{nombre_base}.vrt.ovr" if prefix else f"{nombre_base}.vrt.ovr"
                    s3.upload_file(ovr_local, bucket, ovr_key)
            
            # Limpieza local
            if os.path.exists(vrt_local): os.remove(vrt_local)
            if os.path.exists(ovr_local): os.remove(ovr_local)
                
        except Exception as e:
            print(f"[GIS Service] Error al generar Pirámides en la nube: {e}")
            PROGRESS_STORE[task_id] = -1
            return
    elif ya_existe:
        print("[GIS Service] La imagen ya fue procesada anteriormente. Se omite la recreación de pirámides.")
        PROGRESS_STORE[task_id] = 50.0

    PROGRESS_STORE[task_id] = 85.0
            
    # 3. Guardar en Base de Datos
    print("[GIS Service] Guardando/Actualizando catálogo en PostgreSQL...")
    try:
        base_orig = os.getenv("DIR_ORTOFOTOS_ORIGINALES")
        s3_ruta_completa = f"{base_orig}/{nombre_archivo}" if base_orig else ruta_archivo
        
        q_upsert = text("""
            INSERT INTO catastro.ortofotos_catalogo (nombre_archivo, ruta_completa, srid_original, tipo_archivo, geom, id_provincia, id_canton, id_ciudad)
            VALUES (:nombre, :ruta, :srid, :tipo, ST_Transform(ST_GeomFromText(:wkt, :srid_lec), :srid_dest), :id_prov, :id_can, :id_ciu)
            ON CONFLICT (nombre_archivo) DO UPDATE SET 
                ruta_completa = EXCLUDED.ruta_completa,
                srid_original = EXCLUDED.srid_original,
                tipo_archivo = EXCLUDED.tipo_archivo,
                geom = EXCLUDED.geom,
                id_provincia = EXCLUDED.id_provincia,
                id_canton = EXCLUDED.id_canton,
                id_ciudad = EXCLUDED.id_ciudad
        """)
        
        db.execute(q_upsert, {
            "nombre": nombre_archivo,
            "ruta": s3_ruta_completa,
            "srid": srid_orig,
            "tipo": tipo_archivo,
            "wkt": wkt_geom,
            "srid_lec": srid_lectura,
            "srid_dest": SRID_DESTINO,
            "id_prov": dpa_data.get("id_provincia") if dpa_data else None,
            "id_can": dpa_data.get("id_canton") if dpa_data else None,
            "id_ciu": dpa_data.get("id_ciudad") if dpa_data else None
        })
        db.commit()
        PROGRESS_STORE[task_id] = 100.0
        print(f"[GIS Service] PROCESO EXITOSO. La ortofoto '{nombre_archivo}' ya está en el catálogo.")
    except Exception as e:
        print(f"[GIS Service] Error en BD: {e}")
        PROGRESS_STORE[task_id] = -1
        db.rollback()
