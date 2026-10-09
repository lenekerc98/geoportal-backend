from app.core.ortofoto_service import PROGRESS_STORE
import os
import uuid
import shutil
import zipfile
import subprocess
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any, List, Optional
import math
from shapely import wkt
import shapely



def calcular_rumbo_py(x1: float, y1: float, x2: float, y2: float) -> Optional[str]:
    """Calcula el rumbo topográfico de la línea (x1,y1) -> (x2,y2) en formato N/S dd° mm' ss" E/W"""
    dx = x2 - x1
    dy = y2 - y1
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        return None
    azimuth_rad = math.atan2(dx, dy)
    if azimuth_rad < 0:
        azimuth_rad += 2 * math.pi
    azimuth_deg = math.degrees(azimuth_rad)
    
    if 0 <= azimuth_deg <= 90:
        quadrant = "NE"
        rumbo_deg = azimuth_deg
    elif 90 < azimuth_deg <= 180:
        quadrant = "SE"
        rumbo_deg = 180.0 - azimuth_deg
    elif 180 < azimuth_deg <= 270:
        quadrant = "SW"
        rumbo_deg = azimuth_deg - 180.0
    else:
        quadrant = "NW"
        rumbo_deg = 360.0 - azimuth_deg
        
    d = int(math.floor(rumbo_deg))
    m = int(math.floor((rumbo_deg - d) * 60.0))
    s = round(((rumbo_deg - d) * 60.0 - m) * 60.0)
    if s == 60:
        s = 0
        m += 1
    if m == 60:
        m = 0
        d += 1
        
    return f"{quadrant[0]} {d}° {m}' {s}\" {quadrant[1]}"


def procesar_topologia_predio(geom_wkt: str):
    """
    Dada la geometría WKT en EPSG:32717 UTM:
    1. Obtiene el polígono principal.
    2. Extrae los vértices del anillo exterior sin repetición del último vértice.
    3. Asegura el sentido horario (CW): de izquierda a derecha en el norte.
    4. Identifica el vértice P01: el punto más al norte (mayor Y). Si hay empate, el más a la izquierda (menor X).
    5. Reordena la lista empezando en P01 en sentido horario.
    6. Retorna:
       - vertices: list of dict(codigo='P01', coord_x=..., coord_y=...)
       - linderos: list of dict(tramo='P01 - P02', x1=..., y1=..., x2=..., y2=..., longitud=..., rumbo=...)
    """
    try:
        geom = wkt.loads(geom_wkt)
    except Exception as e:
        logging.warning(f"Error parseando WKT: {e}")
        return [], []

    if geom.geom_type == 'MultiPolygon':
        poly = max(geom.geoms, key=lambda p: p.area)
    elif geom.geom_type == 'Polygon':
        poly = geom
    else:
        return [], []

    raw_coords = list(poly.exterior.coords)
    if len(raw_coords) < 4:
        return [], []

    coords = raw_coords[:-1]

    # Sentido horario (Clockwise)
    if shapely.is_ccw(poly.exterior):
        coords.reverse()

    # P01: Vértice Nor-Oeste (NW) de acuerdo a la norma catastral y topográfica.
    # Normalizamos en el Bounding Box: normY maximiza el Norte [0, 1] y normX minimiza el Este [0, 1].
    # Score = normY - normX (el vértice que esté más al norte de izquierda a derecha).
    min_x = min(c[0] for c in coords)
    max_x = max(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_y = max(c[1] for c in coords)
    span_x = (max_x - min_x) if (max_x - min_x) > 1e-6 else 1.0
    span_y = (max_y - min_y) if (max_y - min_y) > 1e-6 else 1.0

    best_idx = 0
    best_score = -float('inf')
    for idx, (x, y) in enumerate(coords):
        norm_x = (x - min_x) / span_x
        norm_y = (y - min_y) / span_y
        score = norm_y - norm_x
        if score > best_score + 1e-5:
            best_score = score
            best_idx = idx
        elif abs(score - best_score) <= 1e-5:
            cur_x, cur_y = coords[best_idx]
            if y > cur_y or (abs(y - cur_y) <= 1e-5 and x < cur_x):
                best_idx = idx

    rotated = coords[best_idx:] + coords[:best_idx]
    n = len(rotated)

    vertices_list = []
    linderos_list = []

    for i in range(n):
        p1 = rotated[i]
        p2 = rotated[(i + 1) % n]
        cod_v = f"P{i+1:02d}"
        cod_v_next = f"P{((i+1)%n)+1:02d}"
        tramo = f"{cod_v} - {cod_v_next}"
        
        dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        rumbo = calcular_rumbo_py(p1[0], p1[1], p2[0], p2[1])

        vertices_list.append({
            "codigo": cod_v,
            "coord_x": round(p1[0], 4),
            "coord_y": round(p1[1], 4),
        })

        linderos_list.append({
            "tramo": tramo,
            "x1": round(p1[0], 4),
            "y1": round(p1[1], 4),
            "x2": round(p2[0], 4),
            "y2": round(p2[1], 4),
            "longitud": round(dist, 4),
            "rumbo": rumbo
        })

    return vertices_list, linderos_list


def reconstruir_topologia_predio(
    db: Session, 
    predio_id: int, 
    colindantes: Optional[List[str]] = None, 
    rumbos: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Regenera los vértices y linderos del predio indicado:
    - P01 como vértice más al norte (y a la izquierda en caso de empate).
    - Recorrido en sentido horario (CW).
    - Nomenclatura P01, P02...
    - Cálculo de rumbo topográfico y tramo para cada lindero.
    """
    predio_row = db.execute(
        text("SELECT id, cod_catastral, empresa_id, ST_AsText(geom) as geom_wkt FROM catastro.predio WHERE id = :pid"),
        {"pid": predio_id}
    ).mappings().first()

    if not predio_row or not predio_row["geom_wkt"]:
        return {"vertices_creados": 0, "lineas_creadas": 0}

    cod_catastral = predio_row["cod_catastral"]
    empresa_id = predio_row["empresa_id"]
    geom_wkt = predio_row["geom_wkt"]

    vertices_list, linderos_list = procesar_topologia_predio(geom_wkt)
    if not vertices_list:
        return {"vertices_creados": 0, "lineas_creadas": 0}

    # Limpiar vértices y linderos anteriores
    db.execute(text("DELETE FROM catastro.vertice WHERE predio_id = :pid"), {"pid": predio_id})
    db.execute(text("DELETE FROM catastro.linea_lindero WHERE predio_id = :pid"), {"pid": predio_id})

    # Insertar Vértices en lote
    q_vert = text("""
        INSERT INTO catastro.vertice (predio_id, cod_catastral, codigo, coord_x, coord_y, geom, empresa_id)
        VALUES (:pid, :cod, :codigo, :x, :y, ST_SetSRID(ST_MakePoint(:x, :y), 32717), :emp_id)
    """)
    v_params = [
        {
            "pid": predio_id,
            "cod": cod_catastral,
            "codigo": v["codigo"],
            "x": v["coord_x"],
            "y": v["coord_y"],
            "emp_id": empresa_id
        }
        for v in vertices_list
    ]
    if v_params:
        db.execute(q_vert, v_params)

    # Insertar Linderos en lote
    q_lin = text("""
        INSERT INTO catastro.linea_lindero (predio_id, cod_catastral, longitud, rumbo, tramo, colindante, geom, empresa_id)
        VALUES (:pid, :cod, :longitud, :rumbo, :tramo, :colindante, ST_SetSRID(ST_MakeLine(ST_MakePoint(:x1, :y1), ST_MakePoint(:x2, :y2)), 32717), :emp_id)
    """)
    l_params = []
    for idx, l in enumerate(linderos_list):
        val_col = ""
        if colindantes and idx < len(colindantes) and colindantes[idx]:
            val_col = str(colindantes[idx]).strip()
        val_rumbo = l["rumbo"]
        if rumbos and idx < len(rumbos) and rumbos[idx]:
            val_rumbo = str(rumbos[idx]).strip()

        l_params.append({
            "pid": predio_id,
            "cod": cod_catastral,
            "longitud": l["longitud"],
            "rumbo": val_rumbo,
            "tramo": l["tramo"],
            "colindante": val_col,
            "x1": l["x1"],
            "y1": l["y1"],
            "x2": l["x2"],
            "y2": l["y2"],
            "emp_id": empresa_id
        })
    if l_params:
        db.execute(q_lin, l_params)

    return {
        "vertices_creados": len(vertices_list),
        "lineas_creadas": len(linderos_list)
    }

def resolver_contexto_empresa_proyecto(db: Session, empresa_id: Optional[int], proyecto_id: Optional[int] = None):
    """
    Determina proyecto_id, id_provincia e id_canton por defecto a partir de la empresa o proyecto.
    """
    resolved_proyecto_id = proyecto_id
    resolved_id_provincia = None
    resolved_id_canton = None

    if empresa_id:
        try:
            emp = db.execute(text("SELECT id, provincia, canton, proyecto_id FROM catastro.empresa WHERE id = :eid"), {"eid": empresa_id}).mappings().first()
            if emp:
                if not resolved_proyecto_id and emp.get("proyecto_id"):
                    resolved_proyecto_id = emp["proyecto_id"]
                
                if emp.get("provincia"):
                    prov_row = db.execute(text("SELECT id FROM catastro.provincias WHERE lower(nombre) = lower(:p) LIMIT 1"), {"p": emp["provincia"].strip()}).mappings().first()
                    if prov_row:
                        resolved_id_provincia = prov_row["id"]
                        
                if emp.get("canton"):
                    cant_row = db.execute(text("SELECT id FROM catastro.cantones WHERE lower(nombre) = lower(:c) LIMIT 1"), {"c": emp["canton"].strip()}).mappings().first()
                    if cant_row:
                        resolved_id_canton = cant_row["id"]
        except Exception as e:
            logging.warning(f"Error resolviendo contexto empresa-proyecto: {e}")

    return resolved_proyecto_id, resolved_id_provincia, resolved_id_canton

def resolver_dpa_predio(val_cod: str, default_prov: Optional[int], default_cant: Optional[int], db: Session):
    """
    Si el código catastral tiene prefijo DPA válido (primeros 2 dígitos provincia, primeros 4 cantón),
    lo utiliza; si no, utiliza los predeterminados de la empresa/proyecto.
    """
    id_prov = default_prov
    id_cant = default_cant
    if val_cod and not str(val_cod).startswith("TEMP-") and len(str(val_cod)) >= 4 and str(val_cod)[:4].isdigit():
        p_code = str(val_cod)[:2]
        c_code = str(val_cod)[:4]
        try:
            p_row = db.execute(text("SELECT id FROM catastro.provincias WHERE codigo_dpa = :cd LIMIT 1"), {"cd": p_code}).mappings().first()
            if p_row:
                id_prov = p_row["id"]
            c_row = db.execute(text("SELECT id FROM catastro.cantones WHERE codigo_dpa = :cd LIMIT 1"), {"cd": c_code}).mappings().first()
            if c_row:
                id_cant = c_row["id"]
        except Exception as e:
            logging.warning(f"Error resolviendo DPA por código catastral {val_cod}: {e}")
    return id_prov, id_cant

def procesar_shapefile(
    file_path: str, 
    empresa_id: int,
    mapping: Dict[str, str],
    renames: Dict[str, str],
    db: Session,
    import_type: str = "catastro_base",
    nombre_capa: str = None,
    user_id: int = None,
    fecha_creacion: str = None,
    proyecto_id: int = None
) -> Dict[str, Any]:
    """
    Procesa un shapefile (.zip), lo importa a una tabla temporal en PostGIS y luego
    sincroniza Posesionarios, Predios, Vértices y Linderos.
    """
    temp_dir = os.path.join(os.getcwd(), "Temp", f"shape_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)
    
    if not fecha_creacion:
        import datetime
        fecha_creacion = datetime.date.today().isoformat()
    resolved_proyecto_id, default_prov, default_cant = resolver_contexto_empresa_proyecto(db, empresa_id, proyecto_id)

    try:
        # 1. Extraer ZIP con protección Zip Slip
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            base_dir_abs = os.path.abspath(temp_dir)
            for member in zip_ref.namelist():
                dest_path = os.path.abspath(os.path.join(base_dir_abs, member))
                if not dest_path.startswith(base_dir_abs + os.sep) and dest_path != base_dir_abs:
                    raise ValueError(f"Extracción insegura cancelada (Zip Slip): {member}")
            zip_ref.extractall(temp_dir)
            
        # 2. Buscar archivo .shp
        shp_file = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(".shp"):
                    shp_file = os.path.join(root, file)
                    break
            if shp_file:
                break
                
        if not shp_file:
            raise ValueError("No se encontró ningún archivo .shp en el ZIP")

        base_shp = os.path.splitext(shp_file)[0]
        missing_parts = []
        dbf_file = None
        shx_file = None
        for ext in [".dbf", ".DBF"]:
            if os.path.exists(base_shp + ext):
                dbf_file = base_shp + ext
                break
        for ext in [".shx", ".SHX"]:
            if os.path.exists(base_shp + ext):
                shx_file = base_shp + ext
                break

        if not dbf_file:
            missing_parts.append(".dbf")
        if not shx_file:
            missing_parts.append(".shx")
        if missing_parts:
            raise ValueError(f"El shapefile está incompleto. Faltan los componentes obligatorios: {', '.join(missing_parts)}")
            
        # 3. Importar a PostGIS usando ogr2ogr
        tabla_raw = f"shape_{uuid.uuid4().hex[:8]}"
        schema_raw = "catastro"
        tabla_completa = f"{schema_raw}.{tabla_raw}"
        
        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")
            
        # Manejo robusto de codificación de caracteres en DBF
        cpg_file = None
        for ext in [".cpg", ".CPG", ".Cpg"]:
            if os.path.exists(base_shp + ext):
                cpg_file = base_shp + ext
                break

        cpg_val = None
        if cpg_file:
            try:
                with open(cpg_file, 'r', errors='ignore') as f:
                    cpg_val = f.read().strip()
            except Exception:
                pass

        # Validar si el DBF realmente es UTF-8 o contiene bytes en LATIN1/CP1252 (como 'ñ' 0xd1, tildes)
        detected_encoding = "LATIN1"
        if dbf_file and os.path.exists(dbf_file):
            try:
                import struct
                with open(dbf_file, "rb") as f:
                    header = f.read(32)
                    if len(header) >= 12:
                        num_records, header_len, record_len = struct.unpack("<IHH", header[4:12])
                        f.seek(header_len)
                        es_utf8 = True
                        records_to_test = min(500, num_records)
                        for _ in range(records_to_test):
                            chunk = f.read(record_len)
                            if not chunk:
                                break
                            try:
                                chunk.decode("utf-8")
                            except UnicodeDecodeError:
                                es_utf8 = False
                                break
                        if es_utf8 and (cpg_val or "").upper() in ["UTF-8", "UTF8"]:
                            detected_encoding = "UTF-8"
                        elif es_utf8 and not cpg_val:
                            detected_encoding = "UTF-8"
                        else:
                            detected_encoding = "LATIN1"
            except Exception as check_err:
                logging.warning(f"Error analizando cabecera DBF: {check_err}")
                detected_encoding = cpg_val if cpg_val else "LATIN1"
        else:
            detected_encoding = cpg_val if cpg_val else "LATIN1"

        encoding_flags = ["-oo", f"ENCODING={detected_encoding}"]

        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            f"PG:{db_url}",
            shp_file,
            *encoding_flags,
            "-nln", tabla_completa,
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=id",
            "-lco", "PRECISION=NO",
            "-unsetFieldWidth",
            "-nlt", "PROMOTE_TO_MULTI",
            "-overwrite"
        ]
        
        logging.info(f"Ejecutando ogr2ogr con encoding={detected_encoding}: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True)
        stderr_str = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
        stdout_str = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
        
        if result.returncode != 0:
            logging.error(f"Error en ogr2ogr (código {result.returncode}): {stderr_str}")
            raise RuntimeError(f"Error al procesar el archivo espacial con ogr2ogr: {stderr_str}")
            
        import re
        import unicodedata

        SAFE_IDENT = re.compile(r"^[a-zA-Z0-9_]+$")

        # 3.4 Obtener las columnas reales existentes en la tabla importada por ogr2ogr
        col_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = :schema AND table_name = :table
        """)
        col_rows = db.execute(col_query, {"schema": schema_raw, "table": tabla_raw}).fetchall()
        existing_cols = [r[0] for r in col_rows]

        def normalize_col_key(s: str) -> str:
            if not s:
                return ""
            n = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
            return re.sub(r'[^a-zA-Z0-9_]', '_', n).lower().strip('_')

        # Construir tabla de búsqueda rápida (minúsculas, normalizada y truncada a 10 caracteres por DBF)
        col_lookup: Dict[str, str] = {}
        for c in existing_cols:
            c_low = c.lower()
            c_norm = normalize_col_key(c)
            col_lookup[c_low] = c
            col_lookup[c_norm] = c
            if len(c_low) > 10:
                col_lookup[c_low[:10]] = c
            if len(c_norm) > 10:
                col_lookup[c_norm[:10]] = c

        def resolver_columna(col_name: str) -> str:
            if not col_name:
                return None
            c_str = str(col_name).strip()
            if c_str in existing_cols:
                return c_str
            c_low = c_str.lower()
            if c_low in col_lookup:
                return col_lookup[c_low]
            c_norm = normalize_col_key(c_str)
            if c_norm in col_lookup:
                return col_lookup[c_norm]
            if len(c_low) > 10 and c_low[:10] in col_lookup:
                return col_lookup[c_low[:10]]
            if len(c_norm) > 10 and c_norm[:10] in col_lookup:
                return col_lookup[c_norm[:10]]
            for k, real_col in col_lookup.items():
                if k and (k in c_norm or c_norm in k):
                    return real_col
            return None

        # 3.5 Renombrar columnas con resolución dinámica
        for old_col, new_col in list(renames.items()):
            if old_col and new_col and old_col != new_col:
                real_old = resolver_columna(old_col)
                if not real_old:
                    logging.warning(f"Columna para renombrar '{old_col}' no encontrada en {tabla_completa}")
                    continue
                if not SAFE_IDENT.match(str(new_col)):
                    logging.warning(f"Nombre de columna nuevo inválido '{new_col}'")
                    continue
                try:
                    db.execute(text(f'ALTER TABLE {tabla_completa} RENAME COLUMN "{real_old}" TO "{new_col}"'))
                    if real_old in existing_cols:
                        existing_cols.remove(real_old)
                    existing_cols.append(new_col)
                    col_lookup[new_col.lower()] = new_col
                    col_lookup[normalize_col_key(new_col)] = new_col
                    # Actualizar mapping
                    for k, v in list(mapping.items()):
                        if v and (v == old_col or v == real_old or v.lower() == old_col.lower()):
                            mapping[k] = new_col
                except Exception as ren_err:
                    logging.warning(f"Error al renombrar columna {real_old} a {new_col}: {ren_err}")

        # 4. Inyectar empresa_id a la tabla original cruda
        db.execute(text(f"ALTER TABLE {tabla_completa} ADD COLUMN IF NOT EXISTS empresa_id INT"))
        db.execute(text(f"UPDATE {tabla_completa} SET empresa_id = :empresa_id"), {"empresa_id": empresa_id})
        
        # Resolver columnas de mapeo
        col_cedula = resolver_columna(mapping.get("cedula"))
        col_nombre = resolver_columna(mapping.get("nombre_posesionario"))
        col_codigo = resolver_columna(mapping.get("cod_catastral"))
        col_fecha_adju = resolver_columna(mapping.get("fecha_adjudicacion"))
        col_tramite = resolver_columna(mapping.get("numero_tramite"))
        col_institucion = resolver_columna(mapping.get("institucion"))

        if col_cedula and not SAFE_IDENT.match(str(col_cedula)): col_cedula = None
        if col_nombre and not SAFE_IDENT.match(str(col_nombre)): col_nombre = None
        if col_codigo and not SAFE_IDENT.match(str(col_codigo)): col_codigo = None
        if col_fecha_adju and not SAFE_IDENT.match(str(col_fecha_adju)): col_fecha_adju = None
        if col_tramite and not SAFE_IDENT.match(str(col_tramite)): col_tramite = None
        if col_institucion and not SAFE_IDENT.match(str(col_institucion)): col_institucion = None

        logging.info(f"Columnas resueltas: cedula={col_cedula}, nombre={col_nombre}, codigo={col_codigo}, fecha_adju={col_fecha_adju}, tramite={col_tramite}, institucion={col_institucion}")
        
        resultados = {
            "tabla_cruda": tabla_completa,
            "posesionarios_creados": 0,
            "predios_creados": 0,
            "vertices_creados": 0,
            "lineas_creadas": 0
        }
        
        # Flujo 1: Capa Adicional (registrar y mover a elementos_adicionales)
        if import_type == "capa_adicional":
            res_capa = db.execute(
                text("INSERT INTO catastro.capas_adicionales (nombre_capa, tabla_db, empresa_id) VALUES (:nombre, :tabla, :emp_id) RETURNING id"),
                {"nombre": nombre_capa or "Capa Sin Nombre", "tabla": tabla_completa, "emp_id": empresa_id}
            ).mappings().first()
            
            capa_id = res_capa["id"]
            
            db.execute(
                text(f"""
                    INSERT INTO catastro.elementos_adicionales (capa_id, geom, propiedades)
                    SELECT 
                        :capa_id,
                        ST_Force2D(ST_SetSRID(geom, 32717)),
                        row_to_json(t)::jsonb - 'geom' - 'id' || '{{"codigo_catastral": ""}}'::jsonb
                    FROM {tabla_completa} t
                """),
                {"capa_id": capa_id}
            )
            
            db.execute(text(f"DROP TABLE {tabla_completa} CASCADE"))
            db.commit()
            return resultados
            
        # Flujo 2: Módulo Catastral Base
        # 5. Sincronizar Posesionarios
        if col_cedula and col_nombre:
            query_posesionarios = text(f"""
                INSERT INTO catastro.posesionario (cedula, nombre, empresa_id)
                SELECT DISTINCT 
                    TRIM(CAST("{col_cedula}" AS VARCHAR)), 
                    TRIM(CAST("{col_nombre}" AS VARCHAR)), 
                    :empresa_id
                FROM {tabla_completa}
                WHERE "{col_cedula}" IS NOT NULL 
                  AND TRIM(CAST("{col_cedula}" AS VARCHAR)) <> '' 
                  AND "{col_nombre}" IS NOT NULL 
                  AND TRIM(CAST("{col_nombre}" AS VARCHAR)) <> ''
                ON CONFLICT (cedula) DO UPDATE SET nombre = EXCLUDED.nombre
            """)
            res = db.execute(query_posesionarios, {"empresa_id": empresa_id})
            resultados["posesionarios_creados"] = res.rowcount
            
        # 6. Sincronizar Predios y Códigos
        query_leer = f"SELECT id, geom"
        if col_cedula: query_leer += f', "{col_cedula}" as val_cedula'
        if col_nombre: query_leer += f', "{col_nombre}" as val_nombre'
        if col_codigo: query_leer += f', "{col_codigo}" as val_codigo'
        if col_fecha_adju: query_leer += f', "{col_fecha_adju}" as val_fecha_adju'
        if col_tramite: query_leer += f', "{col_tramite}" as val_tramite'
        if col_institucion: query_leer += f', "{col_institucion}" as val_institucion'
        query_leer += f" FROM {tabla_completa}"
        
        filas = db.execute(text(query_leer)).mappings().all()
        
        for fila in filas:
            try:
                with db.begin_nested():
                    # 6.1 Asegurar Código Catastral
                    codigo_asignar = None
                    if col_codigo and 'val_codigo' in fila and fila['val_codigo'] and str(fila['val_codigo']).strip():
                        codigo_asignar = str(fila['val_codigo']).strip()
                    else:
                        codigo_asignar = f"TEMP-{uuid.uuid4().hex[:8]}"
                        
                    posesionario_id = None
                    if col_cedula and 'val_cedula' in fila and fila['val_cedula'] and str(fila['val_cedula']).strip():
                        val_ced = str(fila['val_cedula']).strip()
                        q_pos = text("SELECT id FROM catastro.posesionario WHERE cedula = :cedula")
                        pos_row = db.execute(q_pos, {"cedula": val_ced}).mappings().first()
                        if pos_row:
                            posesionario_id = pos_row['id']
                    elif col_nombre and 'val_nombre' in fila and fila['val_nombre'] and str(fila['val_nombre']).strip():
                        val_nom = str(fila['val_nombre']).strip()
                        q_find_name = text("SELECT id FROM catastro.posesionario WHERE nombre = :nom AND (:emp_id IS NULL OR empresa_id = :emp_id) AND cedula IS NULL LIMIT 1")
                        exist_row = db.execute(q_find_name, {"nom": val_nom, "emp_id": empresa_id}).mappings().first()
                        if exist_row:
                            posesionario_id = exist_row["id"]
                        else:
                            ins_pos = text("INSERT INTO catastro.posesionario (nombre, empresa_id) VALUES (:nom, :emp_id) RETURNING id")
                            posesionario_id = db.execute(ins_pos, {"nom": val_nom, "emp_id": empresa_id}).scalar()
                            
                    db.execute(text("""
                        INSERT INTO catastro.codigo_catastral (codigo, posesionario_id, empresa_id)
                        VALUES (:codigo, :pos_id, :emp_id)
                        ON CONFLICT (codigo) DO UPDATE SET posesionario_id = EXCLUDED.posesionario_id
                    """), {"codigo": codigo_asignar, "pos_id": posesionario_id, "emp_id": empresa_id})
                    
                    # 6.2 Insertar Predio
                    val_fa = str(fila.get('val_fecha_adju', '') or '').strip() or None
                    val_tr = str(fila.get('val_tramite', '') or '').strip() or None
                    val_inst = str(fila.get('val_institucion', '') or '').strip() or None

                    row_id_prov, row_id_cant = resolver_dpa_predio(codigo_asignar, default_prov, default_cant, db)
                    q_predio = text(f"""
                        INSERT INTO catastro.predio (cod_catastral, posesionario_id, empresa_id, geom, area_ha, creado_por, fecha_creacion, fecha_adjudicacion, numero_tramite, institucion, proyecto_id, id_provincia, id_canton)
                        SELECT 
                            :codigo, :pos_id, :emp_id, 
                            CASE 
                                WHEN ST_GeometryType(geom) = 'ST_MultiPolygon' 
                                THEN ST_GeometryN(ST_Force2D(ST_SetSRID(geom, 32717)), 1)
                                ELSE ST_Force2D(ST_SetSRID(geom, 32717))
                            END,
                            ST_Area(ST_Force2D(ST_SetSRID(geom, 32717))) / 10000.0,
                            :creado_por,
                            :fecha_creacion,
                            :fecha_adjudicacion,
                            :numero_tramite,
                            :institucion,
                            :proy_id,
                            :id_prov,
                            :id_cant
                        FROM {tabla_completa} WHERE id = :id_row
                        RETURNING id
                    """)
                    res_predio = db.execute(q_predio, {
                        "codigo": codigo_asignar,
                        "pos_id": posesionario_id,
                        "emp_id": empresa_id,
                        "id_row": fila['id'],
                        "creado_por": user_id,
                        "fecha_creacion": fecha_creacion,
                        "fecha_adjudicacion": val_fa,
                        "numero_tramite": val_tr,
                        "institucion": val_inst,
                        "proy_id": resolved_proyecto_id,
                        "id_prov": row_id_prov,
                        "id_cant": row_id_cant
                    }).mappings().first()
                    
                    if res_predio:
                        predio_id = res_predio["id"]
                        resultados["predios_creados"] += 1
                        
                        # 6.3 y 6.4 Topología ordenada (P01 al norte, horario, rumbos)
                        top_res = reconstruir_topologia_predio(db, predio_id)
                        resultados["vertices_creados"] += top_res["vertices_creados"]
                        resultados["lineas_creadas"] += top_res["lineas_creadas"]
            except Exception as row_err:
                logging.error(f"Error procesando fila {fila['id']} del shapefile: {row_err}")
                continue
                
        # Eliminar tabla temporal al finalizar Catastro Base
        db.execute(text(f"DROP TABLE {tabla_completa} CASCADE"))
        db.commit()
        if task_id:
            PROGRESS_STORE[task_id] = {
                "progress": 100,
                "current": total_items,
                "total": total_items,
                "status": "Importación completada exitosamente"
            }
        return resultados
    except Exception as e:
        db.rollback()
        raise e
    finally:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass


def analizar_shapefile(
    file_path: str,
    empresa_id: int,
    mapping: Dict[str, str],
    renames: Dict[str, str],
    db: Session
) -> Dict[str, Any]:
    """
    Extrae el ZIP y carga a una tabla staging en PostGIS para detectar coincidencias espaciales
    (mismo polígono o solapamiento) y por código con predios existentes en catastro.predio.
    """
    import re
    import unicodedata

    SAFE_IDENT = re.compile(r"^[a-zA-Z0-9_]+$")
    temp_dir = os.path.join(os.getcwd(), "Temp", f"analysis_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            base_dir_abs = os.path.abspath(temp_dir)
            for member in zip_ref.namelist():
                dest_path = os.path.abspath(os.path.join(base_dir_abs, member))
                if not dest_path.startswith(base_dir_abs + os.sep) and dest_path != base_dir_abs:
                    raise ValueError(f"Extracción insegura cancelada (Zip Slip): {member}")
            zip_ref.extractall(temp_dir)

        shp_file = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.lower().endswith(".shp"):
                    shp_file = os.path.join(root, file)
                    break
            if shp_file:
                break

        if not shp_file:
            raise ValueError("No se encontró ningún archivo .shp en el ZIP")

        base_shp = os.path.splitext(shp_file)[0]
        dbf_file = None
        for ext in [".dbf", ".DBF"]:
            if os.path.exists(base_shp + ext):
                dbf_file = base_shp + ext
                break
        if not dbf_file:
            raise ValueError("El shapefile no contiene archivo .dbf obligatorio")

        tabla_staging = f"stg_{uuid.uuid4().hex[:8]}"
        schema_raw = "catastro"
        tabla_completa = f"{schema_raw}.{tabla_staging}"

        db_url = os.getenv("DATABASE_URL", "")
        if db_url.startswith("postgresql+psycopg2://"):
            db_url = db_url.replace("postgresql+psycopg2://", "postgresql://")

        detected_encoding = "LATIN1"
        cpg_file = None
        for ext in [".cpg", ".CPG"]:
            if os.path.exists(base_shp + ext):
                cpg_file = base_shp + ext
                break
        if cpg_file:
            try:
                with open(cpg_file, 'r', errors='ignore') as f:
                    val = f.read().strip()
                    if val.upper() in ["UTF-8", "UTF8"]:
                        detected_encoding = "UTF-8"
            except Exception:
                pass

        cmd = [
            "ogr2ogr",
            "-f", "PostgreSQL",
            f"PG:{db_url}",
            shp_file,
            "-oo", f"ENCODING={detected_encoding}",
            "-nln", tabla_completa,
            "-lco", "GEOMETRY_NAME=geom",
            "-lco", "FID=id",
            "-lco", "PRECISION=NO",
            "-unsetFieldWidth",
            "-nlt", "PROMOTE_TO_MULTI",
            "-overwrite"
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            err_msg = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
            raise RuntimeError(f"Error cargando shapefile en staging con ogr2ogr: {err_msg}")

        # Column resolution
        col_rows = db.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_schema = '{schema_raw}' AND table_name = '{tabla_staging}'")).fetchall()
        existing_cols = [r[0] for r in col_rows]

        def normalize_col_key(s: str) -> str:
            if not s: return ""
            n = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
            return re.sub(r'[^a-zA-Z0-9_]', '_', n).lower().strip('_')

        col_lookup = {}
        for c in existing_cols:
            c_low = c.lower()
            c_norm = normalize_col_key(c)
            col_lookup[c_low] = c
            col_lookup[c_norm] = c
            if len(c_low) > 10: col_lookup[c_low[:10]] = c
            if len(c_norm) > 10: col_lookup[c_norm[:10]] = c

        def resolver_columna(col_name: str) -> str:
            if not col_name: return None
            c_str = str(col_name).strip()
            if c_str in existing_cols: return c_str
            c_low = c_str.lower()
            if c_low in col_lookup: return col_lookup[c_low]
            c_norm = normalize_col_key(c_str)
            if c_norm in col_lookup: return col_lookup[c_norm]
            for k, real_col in col_lookup.items():
                if k and (k in c_norm or c_norm in k): return real_col
            return None

        for old_col, new_col in list(renames.items()):
            if old_col and new_col and old_col != new_col:
                real_old = resolver_columna(old_col)
                if real_old and SAFE_IDENT.match(str(new_col)):
                    try:
                        db.execute(text(f'ALTER TABLE {tabla_completa} RENAME COLUMN "{real_old}" TO "{new_col}"'))
                        if real_old in existing_cols: existing_cols.remove(real_old)
                        existing_cols.append(new_col)
                        col_lookup[new_col.lower()] = new_col
                        for k, v in list(mapping.items()):
                            if v and (v == old_col or v == real_old): mapping[k] = new_col
                    except Exception:
                        pass

        col_cedula = resolver_columna(mapping.get("cedula"))
        col_nombre = resolver_columna(mapping.get("nombre_posesionario"))
        col_codigo = resolver_columna(mapping.get("cod_catastral"))
        col_fecha_adju = resolver_columna(mapping.get("fecha_adjudicacion"))
        col_tramite = resolver_columna(mapping.get("numero_tramite"))
        col_institucion = resolver_columna(mapping.get("institucion"))

        # Extraer todos los registros de la tabla staging
        q_cols = ["t.id", "ROUND((ST_Area(ST_Force2D(ST_SetSRID(t.geom, 32717))) / 10000.0)::numeric, 4) as area_ha"]
        if col_codigo: q_cols.append(f'CAST(t."{col_codigo}" AS VARCHAR) as incoming_codigo')
        else: q_cols.append("NULL as incoming_codigo")
        if col_nombre: q_cols.append(f'CAST(t."{col_nombre}" AS VARCHAR) as incoming_propietario')
        else: q_cols.append("NULL as incoming_propietario")
        if col_cedula: q_cols.append(f'CAST(t."{col_cedula}" AS VARCHAR) as incoming_cedula')
        else: q_cols.append("NULL as incoming_cedula")
        if col_fecha_adju: q_cols.append(f'CAST(t."{col_fecha_adju}" AS VARCHAR) as incoming_fecha_adju')
        else: q_cols.append("NULL as incoming_fecha_adju")
        if col_tramite: q_cols.append(f'CAST(t."{col_tramite}" AS VARCHAR) as incoming_tramite')
        else: q_cols.append("NULL as incoming_tramite")
        if col_institucion: q_cols.append(f'CAST(t."{col_institucion}" AS VARCHAR) as incoming_institucion')
        else: q_cols.append("NULL as incoming_institucion")

        all_features_q = text(f"SELECT {', '.join(q_cols)} FROM {tabla_completa} t WHERE t.geom IS NOT NULL ORDER BY t.id ASC")
        all_features = [dict(r) for r in db.execute(all_features_q).mappings().all()]

        # Buscar conflictos espaciales o de código con catastro.predio
        q_conflictos = text(f"""
            SELECT 
                t.id as temp_id,
                p.id as existing_id,
                p.cod_catastral as existing_codigo,
                pos.nombre as existing_propietario,
                pos.cedula as existing_cedula,
                ROUND(p.area_ha::numeric, 4) as existing_area_ha,
                p.fecha_adjudicacion as existing_fecha_adju,
                p.numero_tramite as existing_tramite,
                p.institucion as existing_institucion,
                ST_Equals(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom) as exact_geom,
                ROUND((
                    ST_Area(ST_Intersection(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom)) / 
                    NULLIF(GREATEST(ST_Area(ST_Force2D(ST_SetSRID(t.geom, 32717))), ST_Area(p.geom)), 0) * 100
                )::numeric, 1) as overlap_pct
            FROM {tabla_completa} t
            JOIN catastro.predio p ON (
                (:empresa_id IS NULL OR p.empresa_id = :empresa_id)
                AND (p.fecha_baja IS NULL)
                AND (
                    ST_Equals(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom)
                    OR ST_Intersects(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom)
                    OR (
                        {f'TRIM(CAST(t."{col_codigo}" AS VARCHAR)) = p.cod_catastral' if col_codigo else 'FALSE'}
                    )
                )
            )
            LEFT JOIN catastro.posesionario pos ON p.posesionario_id = pos.id
            WHERE (
                ST_Equals(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom)
                OR (
                    ST_Area(ST_Intersection(ST_Force2D(ST_SetSRID(t.geom, 32717)), p.geom)) / 
                    NULLIF(LEAST(ST_Area(ST_Force2D(ST_SetSRID(t.geom, 32717))), ST_Area(p.geom)), 0) > 0.4
                )
                OR (
                    {f'TRIM(CAST(t."{col_codigo}" AS VARCHAR)) = p.cod_catastral' if col_codigo else 'FALSE'}
                )
            )
            ORDER BY t.id ASC
        """)

        conflicts_rows = db.execute(q_conflictos, {"empresa_id": empresa_id}).mappings().all()

        features_by_id = {f['id']: f for f in all_features}
        conflict_temp_ids = set()
        conflictos = []

        for row in conflicts_rows:
            tid = row['temp_id']
            if tid in conflict_temp_ids:
                continue # Evitar duplicar si intersecta con más de uno
            conflict_temp_ids.add(tid)
            f_in = features_by_id.get(tid, {})

            overlap = float(row['overlap_pct']) if row['overlap_pct'] is not None else 0.0
            is_exact = bool(row['exact_geom']) or overlap >= 90.0

            tipo = "mismo_poligono" if is_exact else ("mismo_codigo" if (col_codigo and f_in.get('incoming_codigo') == row['existing_codigo']) else "solapamiento")

            conflictos.append({
                "temp_id": tid,
                "incoming": {
                    "codigo": f_in.get("incoming_codigo") or "S/C",
                    "propietario": f_in.get("incoming_propietario") or "S/D",
                    "cedula": f_in.get("incoming_cedula") or "",
                    "area_ha": float(f_in.get("area_ha") or 0.0),
                    "fecha_adjudicacion": f_in.get("incoming_fecha_adju"),
                    "numero_tramite": f_in.get("incoming_tramite"),
                    "institucion": f_in.get("incoming_institucion"),
                },
                "existing": {
                    "id": row["existing_id"],
                    "codigo": row["existing_codigo"] or "S/C",
                    "propietario": row["existing_propietario"] or "S/D",
                    "cedula": row["existing_cedula"] or "",
                    "area_ha": float(row["existing_area_ha"] or 0.0),
                    "fecha_adjudicacion": row["existing_fecha_adju"],
                    "numero_tramite": row["existing_tramite"],
                    "institucion": row["existing_institucion"],
                },
                "overlap_pct": overlap,
                "match_type": tipo
            })

        nuevos = []
        for feat in all_features:
            tid = feat['id']
            if tid not in conflict_temp_ids:
                nuevos.append({
                    "temp_id": tid,
                    "codigo": feat.get("incoming_codigo") or "S/C",
                    "propietario": feat.get("incoming_propietario") or "S/D",
                    "cedula": feat.get("incoming_cedula") or "",
                    "area_ha": float(feat.get("area_ha") or 0.0),
                    "fecha_adjudicacion": feat.get("incoming_fecha_adju"),
                    "numero_tramite": feat.get("incoming_tramite"),
                    "institucion": feat.get("incoming_institucion")
                })

        db.commit()
        return {
            "staging_table": tabla_completa,
            "total_features": len(all_features),
            "conflictos": conflictos,
            "nuevos": nuevos
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        try:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception:
            pass


def confirmar_importacion_shapefile(
    staging_table: str,
    empresa_id: int,
    mapping: Dict[str, str],
    conflict_actions: Dict[str, str],
    selected_new_ids: List[int],
    db: Session,
    user_id: int = None,
    fecha_creacion: str = None,
    task_id: str = None,
    proyecto_id: int = None
) -> Dict[str, Any]:
    """
    Aplica las decisiones del usuario:
    - 'reemplazar': actualiza predio existente en BD con la nueva geometría y atributos de staging_table.
    - 'omitir': no altera el predio existente.
    - selected_new_ids: crea nuevos predios en catastro.predio.
    """
    import re
    import unicodedata

    SAFE_IDENT = re.compile(r"^[a-zA-Z0-9_.]+$")
    if not SAFE_IDENT.match(staging_table):
        raise ValueError("Nombre de tabla staging inválido")

    try:
        col_rows = db.execute(text(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{staging_table.split('.')[-1]}'")).fetchall()
        existing_cols = [r[0] for r in col_rows]

        def normalize_col_key(s: str) -> str:
            if not s: return ""
            n = ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn')
            return re.sub(r'[^a-zA-Z0-9_]', '_', n).lower().strip('_')

        col_lookup = {}
        for c in existing_cols:
            col_lookup[c.lower()] = c
            col_lookup[normalize_col_key(c)] = c

        def resolver_columna(col_name: str) -> str:
            if not col_name: return None
            c_str = str(col_name).strip()
            if c_str in existing_cols: return c_str
            if c_str.lower() in col_lookup: return col_lookup[c_str.lower()]
            norm = normalize_col_key(c_str)
            if norm in col_lookup: return col_lookup[norm]
            return None

        col_cedula = resolver_columna(mapping.get("cedula"))
        col_nombre = resolver_columna(mapping.get("nombre_posesionario"))
        col_codigo = resolver_columna(mapping.get("cod_catastral"))
        col_fecha_adju = resolver_columna(mapping.get("fecha_adjudicacion"))
        col_tramite = resolver_columna(mapping.get("numero_tramite"))
        col_institucion = resolver_columna(mapping.get("institucion"))

        # Consultar filas de staging
        q_cols = ["id", "geom", "ST_Area(ST_Force2D(ST_SetSRID(geom, 32717))) / 10000.0 as area_ha"]
        if col_codigo: q_cols.append(f'"{col_codigo}" as val_codigo')
        if col_nombre: q_cols.append(f'"{col_nombre}" as val_nombre')
        if col_cedula: q_cols.append(f'"{col_cedula}" as val_cedula')
        if col_fecha_adju: q_cols.append(f'"{col_fecha_adju}" as val_fecha_adju')
        if col_tramite: q_cols.append(f'"{col_tramite}" as val_tramite')
        if col_institucion: q_cols.append(f'"{col_institucion}" as val_institucion')

        staging_rows = db.execute(text(f"SELECT {', '.join(q_cols)} FROM {staging_table}")).mappings().all()
        staging_dict = {str(r["id"]): r for r in staging_rows}

        resultados = {
            "predios_reemplazados": 0,
            "predios_omitidos": 0,
            "predios_creados": 0,
            "vertices_creados": 0,
            "lineas_creadas": 0
        }

        total_items = max(1, len(conflict_actions) + len(selected_new_ids))
        processed_count = 0
        if task_id:
            PROGRESS_STORE[task_id] = {
                "progress": 0,
                "current": 0,
                "total": total_items,
                "status": f"Iniciando importación de {total_items} elementos..."
            }

        # 1. Procesar conflictos
        for temp_id_str, accion in conflict_actions.items():
            processed_count += 1
            if task_id and (processed_count % 3 == 0 or processed_count == total_items):
                PROGRESS_STORE[task_id] = {
                    "progress": round((processed_count / total_items) * 100, 1),
                    "current": processed_count,
                    "total": total_items,
                    "status": f"Resolviendo conflicto {processed_count} de {total_items}..."
                }
            if str(temp_id_str) not in staging_dict:
                continue
            fila = staging_dict[str(temp_id_str)]

            if accion == "omitir":
                resultados["predios_omitidos"] += 1
                continue

            if accion == "reemplazar":
                val_cod = str(fila.get("val_codigo", "") or "").strip()
                val_nom = str(fila.get("val_nombre", "") or "").strip()
                val_ced = str(fila.get("val_cedula", "") or "").strip()
                val_fa = str(fila.get("val_fecha_adju", "") or "").strip() or None
                val_tr = str(fila.get("val_tramite", "") or "").strip() or None
                val_inst = str(fila.get("val_institucion", "") or "").strip() or None

                # Encontrar el predio existente que colisiona con esta fila de staging
                q_find = text(f"""
                    SELECT p.id, p.cod_catastral
                    FROM catastro.predio p
                    WHERE (:empresa_id IS NULL OR p.empresa_id = :empresa_id)
                      AND p.fecha_baja IS NULL
                      AND (
                          ST_Equals(ST_Force2D(ST_SetSRID((SELECT geom FROM {staging_table} WHERE id = :tid), 32717)), p.geom)
                          OR (
                              ST_Intersects(ST_Force2D(ST_SetSRID((SELECT geom FROM {staging_table} WHERE id = :tid), 32717)), p.geom)
                              AND ST_Area(ST_Intersection(ST_Force2D(ST_SetSRID((SELECT geom FROM {staging_table} WHERE id = :tid), 32717)), p.geom)) / 
                                  NULLIF(LEAST(ST_Area(ST_Force2D(ST_SetSRID((SELECT geom FROM {staging_table} WHERE id = :tid), 32717))), ST_Area(p.geom)), 0) > 0.4
                          )
                          OR (:cod IS NOT NULL AND :cod != '' AND p.cod_catastral = :cod)
                      )
                    LIMIT 1
                """)
                target = db.execute(q_find, {"empresa_id": empresa_id, "tid": int(temp_id_str), "cod": val_cod}).mappings().first()

                if target:
                    target_id = target["id"]
                    final_cod = val_cod if val_cod else target["cod_catastral"]

                    # Actualizar posesionario si viene nombre o cédula
                    posesionario_id = None
                    if val_ced or val_nom:
                        if val_ced:
                            q_pos = text("SELECT id FROM catastro.posesionario WHERE cedula = :cedula")
                            pos_row = db.execute(q_pos, {"cedula": val_ced}).mappings().first()
                            if pos_row:
                                posesionario_id = pos_row["id"]
                                if val_nom:
                                    db.execute(text("UPDATE catastro.posesionario SET nombre = :nom WHERE id = :id"), {"nom": val_nom, "id": posesionario_id})
                            else:
                                ins_pos = text("INSERT INTO catastro.posesionario (cedula, nombre, empresa_id) VALUES (:ced, :nom, :emp_id) RETURNING id")
                                posesionario_id = db.execute(ins_pos, {"ced": val_ced, "nom": val_nom, "emp_id": empresa_id}).scalar()
                        elif val_nom:
                            q_find_name = text("SELECT id FROM catastro.posesionario WHERE nombre = :nom AND (:emp_id IS NULL OR empresa_id = :emp_id) AND cedula IS NULL LIMIT 1")
                            exist_row = db.execute(q_find_name, {"nom": val_nom, "emp_id": empresa_id}).mappings().first()
                            if exist_row:
                                posesionario_id = exist_row["id"]
                            else:
                                ins_pos = text("INSERT INTO catastro.posesionario (nombre, empresa_id) VALUES (:nom, :emp_id) RETURNING id")
                                posesionario_id = db.execute(ins_pos, {"nom": val_nom, "emp_id": empresa_id}).scalar()

                    row_id_prov, row_id_cant = resolver_dpa_predio(final_cod, default_prov, default_cant, db)
                    # Actualizar predio existente
                    q_upd = text(f"""
                        UPDATE catastro.predio
                        SET 
                            geom = (
                                SELECT CASE 
                                    WHEN ST_GeometryType(geom) = 'ST_MultiPolygon' 
                                    THEN ST_GeometryN(ST_Force2D(ST_SetSRID(geom, 32717)), 1)
                                    ELSE ST_Force2D(ST_SetSRID(geom, 32717))
                                END
                                FROM {staging_table} WHERE id = :tid
                            ),
                            area_ha = (SELECT ST_Area(ST_Force2D(ST_SetSRID(geom, 32717))) / 10000.0 FROM {staging_table} WHERE id = :tid),
                            cod_catastral = COALESCE(:cod, cod_catastral),
                            posesionario_id = COALESCE(:pos_id, posesionario_id),
                            fecha_adjudicacion = COALESCE(:fa, fecha_adjudicacion),
                            numero_tramite = COALESCE(:tr, numero_tramite),
                            institucion = COALESCE(:inst, institucion),
                            proyecto_id = COALESCE(proyecto_id, :proy_id),
                            id_provincia = COALESCE(id_provincia, :id_prov),
                            id_canton = COALESCE(id_canton, :id_cant),
                            modificado_por = :mod_por,
                            fecha_modificacion = NOW()
                        WHERE id = :target_id
                    """)
                    db.execute(q_upd, {
                        "tid": int(temp_id_str),
                        "cod": final_cod,
                        "pos_id": posesionario_id,
                        "fa": val_fa,
                        "tr": val_tr,
                        "inst": val_inst,
                        "mod_por": user_id,
                        "target_id": target_id,
                        "proy_id": resolved_proyecto_id,
                        "id_prov": row_id_prov,
                        "id_cant": row_id_cant
                    })

                    # Regenerar vértices y linderos ordenados (P01 al norte, horario, rumbos)
                    top_res = reconstruir_topologia_predio(db, target_id)
                    resultados["vertices_creados"] += top_res["vertices_creados"]
                    resultados["lineas_creadas"] += top_res["lineas_creadas"]
                    resultados["predios_reemplazados"] += 1

        # 2. Procesar predios nuevos seleccionados
        selected_set = set(str(sid) for sid in selected_new_ids)
        for sid_str in selected_set:
            processed_count += 1
            if task_id and (processed_count % 2 == 0 or processed_count == total_items or processed_count == 1):
                PROGRESS_STORE[task_id] = {
                    "progress": round((processed_count / total_items) * 100, 1),
                    "current": processed_count,
                    "total": total_items,
                    "status": f"Importando predio {processed_count} de {total_items}..."
                }
            if sid_str not in staging_dict:
                continue
            fila = staging_dict[sid_str]

            val_cod = str(fila.get("val_codigo", "") or "").strip() or f"TEMP-{uuid.uuid4().hex[:8]}"
            val_nom = str(fila.get("val_nombre", "") or "").strip()
            val_ced = str(fila.get("val_cedula", "") or "").strip()
            val_fa = str(fila.get("val_fecha_adju", "") or "").strip() or None
            val_tr = str(fila.get("val_tramite", "") or "").strip() or None
            val_inst = str(fila.get("val_institucion", "") or "").strip() or None

            posesionario_id = None
            if val_ced:
                q_pos = text("SELECT id FROM catastro.posesionario WHERE cedula = :cedula")
                pos_row = db.execute(q_pos, {"cedula": val_ced}).mappings().first()
                if pos_row:
                    posesionario_id = pos_row["id"]
                else:
                    ins_pos = text("INSERT INTO catastro.posesionario (cedula, nombre, empresa_id) VALUES (:ced, :nom, :emp_id) RETURNING id")
                    posesionario_id = db.execute(ins_pos, {"ced": val_ced, "nom": val_nom or "S/D", "emp_id": empresa_id}).scalar()
            elif val_nom:
                q_find_name = text("SELECT id FROM catastro.posesionario WHERE nombre = :nom AND (:emp_id IS NULL OR empresa_id = :emp_id) AND cedula IS NULL LIMIT 1")
                exist_row = db.execute(q_find_name, {"nom": val_nom, "emp_id": empresa_id}).mappings().first()
                if exist_row:
                    posesionario_id = exist_row["id"]
                else:
                    ins_pos = text("INSERT INTO catastro.posesionario (nombre, empresa_id) VALUES (:nom, :emp_id) RETURNING id")
                    posesionario_id = db.execute(ins_pos, {"nom": val_nom, "emp_id": empresa_id}).scalar()

            # Código catastral
            db.execute(text("""
                INSERT INTO catastro.codigo_catastral (codigo, posesionario_id, empresa_id)
                VALUES (:codigo, :pos_id, :emp_id)
                ON CONFLICT (codigo) DO UPDATE SET posesionario_id = EXCLUDED.posesionario_id
            """), {"codigo": val_cod, "pos_id": posesionario_id, "emp_id": empresa_id})

            row_id_prov, row_id_cant = resolver_dpa_predio(val_cod, default_prov, default_cant, db)
            # Predio
            q_ins = text(f"""
                INSERT INTO catastro.predio (cod_catastral, posesionario_id, empresa_id, geom, area_ha, creado_por, fecha_creacion, fecha_adjudicacion, numero_tramite, institucion, proyecto_id, id_provincia, id_canton)
                SELECT 
                    :codigo, :pos_id, :emp_id,
                    CASE 
                        WHEN ST_GeometryType(geom) = 'ST_MultiPolygon' 
                        THEN ST_GeometryN(ST_Force2D(ST_SetSRID(geom, 32717)), 1)
                        ELSE ST_Force2D(ST_SetSRID(geom, 32717))
                    END,
                    ST_Area(ST_Force2D(ST_SetSRID(geom, 32717))) / 10000.0,
                    :creado_por, :fecha_creacion, :fa, :tr, :inst,
                    :proy_id, :id_prov, :id_cant
                FROM {staging_table} WHERE id = :id_row
                RETURNING id
            """)
            new_predio = db.execute(q_ins, {
                "codigo": val_cod,
                "pos_id": posesionario_id,
                "emp_id": empresa_id,
                "id_row": int(sid_str),
                "creado_por": user_id,
                "fecha_creacion": fecha_creacion,
                "fa": val_fa,
                "tr": val_tr,
                "inst": val_inst,
                "proy_id": resolved_proyecto_id,
                "id_prov": row_id_prov,
                "id_cant": row_id_cant
            }).mappings().first()

            if new_predio:
                new_id = new_predio["id"]
                resultados["predios_creados"] += 1

                # Topología ordenada (P01 al norte, horario, rumbos)
                top_res = reconstruir_topologia_predio(db, new_id)
                resultados["vertices_creados"] += top_res["vertices_creados"]
                resultados["lineas_creadas"] += top_res["lineas_creadas"]

        # Limpiar tabla staging
        db.execute(text(f"DROP TABLE IF EXISTS {staging_table} CASCADE"))
        db.commit()
        if task_id:
            PROGRESS_STORE[task_id] = {
                "progress": 100,
                "current": total_items,
                "total": total_items,
                "status": "Importación completada exitosamente"
            }
        return resultados
    except Exception as e:
        db.rollback()
        raise e
