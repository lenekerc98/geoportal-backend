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
    Procesa la ortofoto en segundo plano:
    - Mueve la foto a Ortofotos/Complementos/YYYY/MM/
    - Si ya existe en BD, omite las pirámides (Inteligencia de Archivo).
    - Genera pirámides (.ovr) si es nueva.
    - Reconstruye el VRT Maestro con TODAS las fotos de la base.
    - Guarda/actualiza en PostgreSQL.
    """
    PROGRESS_STORE[task_id] = 1.0
    print(f"[GIS Service] Iniciando procesamiento: {ruta_archivo}")
    
    if not os.path.exists(ruta_archivo):
        print(f"[GIS Service] Error: El archivo no existe: {ruta_archivo}")
        PROGRESS_STORE[task_id] = -1
        return
        
    nombre_archivo = os.path.basename(ruta_archivo)
    tipo_archivo = nombre_archivo.split('.')[-1].lower() if '.' in nombre_archivo else 'desconocido'
    
    # 0. Mover el TIF original a Ortofotos/Ortofotos/ si no está ahí
    nueva_ruta = os.path.join(ORTOFOTOS_DIR, nombre_archivo)
    
    if os.path.abspath(ruta_archivo) != os.path.abspath(nueva_ruta):
        print(f"[GIS Service] Moviendo TIF a la carpeta de Ortofotos: {nueva_ruta}")
        shutil.move(ruta_archivo, nueva_ruta)
    
    # 1. Obtener datos geográficos del TIF
    wkt_geom, srid_orig = obtener_datos_ortofoto(nueva_ruta)
    if not wkt_geom:
        print("[GIS Service] Error: No se pudo obtener la geometría.")
        PROGRESS_STORE[task_id] = -1
        return
        
    srid_lectura = srid_orig if srid_orig else SRID_DESTINO

    # Verificar si YA fue procesada
    q_check = text("SELECT id FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :nombre")
    ya_existe = db.execute(q_check, {"nombre": nombre_archivo}).fetchone() is not None
    
    # Ruta del VRT individual y su OVR en Complementos
    nombre_base = os.path.splitext(nombre_archivo)[0]
    vrt_individual = os.path.join(COMPLEMENTOS_DIR, f"{nombre_base}.vrt")
    tiene_ovr = os.path.exists(vrt_individual + '.ovr')

    # 2. Construir VRT individual en Complementos y generarle pirámides allí
    if tipo_archivo in ['tif', 'tiff', 'ecw', 'jp2'] and (not ya_existe or not tiene_ovr):
        PROGRESS_STORE[task_id] = 10.0
        try:
            print("[GIS Service] Creando VRT individual en Complementos para aislar el OVR...")
            gdal.BuildVRT(vrt_individual, [nueva_ruta])
            
            print("[GIS Service] Construyendo pirámides en Complementos...")
            ds_individual = gdal.Open(vrt_individual, gdal.GA_Update)
            if ds_individual:
                ds_individual.BuildOverviews("AVERAGE", [2, 4, 8, 16, 32, 64], callback=gdal_progress_callback, callback_data=task_id)
                ds_individual = None
            else:
                print("[GIS Service] Advertencia: No se pudo abrir VRT para pirámides.")
        except Exception as e:
            print(f"[GIS Service] Error al generar Pirámides: {e}")
            PROGRESS_STORE[task_id] = -1
            return
    elif ya_existe and tiene_ovr:
        print("[GIS Service] La imagen ya fue procesada anteriormente y tiene pirámides. Se omite la recreación.")
        PROGRESS_STORE[task_id] = 50.0

    # 3. Reconstruir el VRT Maestro con TODAS las ortofotos (Mosaico)
    if tipo_archivo in ['tif', 'tiff', 'ecw', 'jp2']:
        print("[GIS Service] Actualizando el Mosaico VRT Maestro...")
        try:
            # Obtenemos todos los TIF del catálogo
            fotos_db = db.execute(text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE tipo_archivo != 'vrt'")).fetchall()
            rutas_tif = [f[0] for f in fotos_db if os.path.exists(f[0])]
            if nueva_ruta not in rutas_tif:
                rutas_tif.append(nueva_ruta)
            
            if rutas_tif:
                gdal.BuildVRT(VRT_FILE, rutas_tif)
                print("[GIS Service] VRT Maestro actualizado.")
        except Exception as e:
            print(f"[GIS Service] Error reconstruyendo VRT: {e}")
            
    PROGRESS_STORE[task_id] = 85.0
            
    # 4. Guardar en Base de Datos
    print("[GIS Service] Guardando/Actualizando catálogo en PostgreSQL...")
    try:
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
            "ruta": nueva_ruta,
            "srid": srid_orig,
            "tipo": tipo_archivo,
            "wkt": wkt_geom,
            "srid_lec": srid_lectura,
            "srid_dest": SRID_DESTINO,
            "id_prov": dpa_data.get("id_provincia") if dpa_data else None,
            "id_can": dpa_data.get("id_canton") if dpa_data else None,
            "id_ciu": dpa_data.get("id_ciudad") if dpa_data else None
        })
        
        # Registrar el VRT Maestro
        if os.path.exists(VRT_FILE):
            wkt_vrt, srid_vrt = obtener_datos_ortofoto(VRT_FILE)
            if wkt_vrt:
                db.execute(q_upsert, {
                    "nombre": "ortofotos.vrt",
                    "ruta": VRT_FILE,
                    "srid": srid_vrt,
                    "tipo": "vrt",
                    "wkt": wkt_vrt,
                    "srid_lec": srid_vrt or SRID_DESTINO,
                    "srid_dest": SRID_DESTINO,
                    "id_prov": None,
                    "id_can": None,
                    "id_ciu": None
                })
        
        db.commit()
        PROGRESS_STORE[task_id] = 100.0 # Completado!
        print(f"[GIS Service] PROCESO EXITOSO. La ortofoto '{nombre_archivo}' ya está en el catálogo.")
    except Exception as e:
        print(f"[GIS Service] Error en BD: {e}")
        PROGRESS_STORE[task_id] = -1
        db.rollback()
