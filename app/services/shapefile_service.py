import os
import uuid
import shutil
import zipfile
import subprocess
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging
from typing import Dict, Any, List

def procesar_shapefile(
    file_path: str, 
    empresa_id: int,
    mapping: Dict[str, str],
    renames: Dict[str, str],
    db: Session,
    import_type: str = "catastro_base",
    nombre_capa: str = None,
    user_id: int = None
) -> Dict[str, Any]:
    """
    Procesa un shapefile (.zip), lo importa a una tabla temporal en PostGIS y luego
    sincroniza Posesionarios, Predios, Vértices y Linderos.
    """
    temp_dir = os.path.join(os.getcwd(), "Temp", f"shape_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)
    
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
        SAFE_IDENT = re.compile(r"^[a-zA-Z0-9_]+$")

        # 3.5 Renombrar columnas con validación estricta de identificadores
        for old_col, new_col in list(renames.items()):
            if old_col and new_col and old_col != new_col:
                if not SAFE_IDENT.match(str(old_col)) or not SAFE_IDENT.match(str(new_col)):
                    logging.warning(f"Columna descartada por contener caracteres sospechosos: {old_col} -> {new_col}")
                    continue
                try:
                    db.execute(text(f'ALTER TABLE {tabla_completa} RENAME COLUMN "{old_col}" TO "{new_col}"'))
                    # Actualizar el mapping para que apunte al nuevo nombre
                    for k, v in mapping.items():
                        if v == old_col:
                            mapping[k] = new_col
                except Exception as ren_err:
                    logging.warning(f"Error al renombrar columna {old_col} a {new_col}: {ren_err}")

        # 4. Inyectar empresa_id a la tabla original cruda
        db.execute(text(f"ALTER TABLE {tabla_completa} ADD COLUMN IF NOT EXISTS empresa_id INT"))
        db.execute(text(f"UPDATE {tabla_completa} SET empresa_id = :empresa_id"), {"empresa_id": empresa_id})
        
        col_cedula = mapping.get("cedula")
        col_nombre = mapping.get("nombre_posesionario")
        col_codigo = mapping.get("cod_catastral")

        if col_cedula and not SAFE_IDENT.match(str(col_cedula)): col_cedula = None
        if col_nombre and not SAFE_IDENT.match(str(col_nombre)): col_nombre = None
        if col_codigo and not SAFE_IDENT.match(str(col_codigo)): col_codigo = None
        
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
                SELECT DISTINCT CAST("{col_cedula}" AS VARCHAR), CAST("{col_nombre}" AS VARCHAR), :empresa_id
                FROM {tabla_completa}
                WHERE "{col_cedula}" IS NOT NULL AND "{col_nombre}" IS NOT NULL
                ON CONFLICT (cedula) DO UPDATE SET nombre = EXCLUDED.nombre
            """)
            res = db.execute(query_posesionarios, {"empresa_id": empresa_id})
            resultados["posesionarios_creados"] = res.rowcount
            
        # 6. Sincronizar Predios y Códigos
        query_leer = f"SELECT id, geom"
        if col_cedula: query_leer += f', "{col_cedula}" as val_cedula'
        if col_codigo: query_leer += f', "{col_codigo}" as val_codigo'
        query_leer += f" FROM {tabla_completa}"
        
        filas = db.execute(text(query_leer)).mappings().all()
        
        for fila in filas:
            try:
                # 6.1 Asegurar Código Catastral
                codigo_asignar = None
                if col_codigo and 'val_codigo' in fila and fila['val_codigo']:
                    codigo_asignar = str(fila['val_codigo'])
                else:
                    codigo_asignar = f"TEMP-{uuid.uuid4().hex[:8]}"
                    
                posesionario_id = None
                if col_cedula and 'val_cedula' in fila and fila['val_cedula']:
                    q_pos = text("SELECT id FROM catastro.posesionario WHERE cedula = :cedula")
                    pos_row = db.execute(q_pos, {"cedula": str(fila['val_cedula'])}).mappings().first()
                    if pos_row:
                        posesionario_id = pos_row['id']
                        
                db.execute(text("""
                    INSERT INTO catastro.codigo_catastral (codigo, posesionario_id, empresa_id)
                    VALUES (:codigo, :pos_id, :emp_id)
                    ON CONFLICT (codigo) DO UPDATE SET posesionario_id = EXCLUDED.posesionario_id
                """), {"codigo": codigo_asignar, "pos_id": posesionario_id, "emp_id": empresa_id})
                
                # 6.2 Insertar Predio
                q_predio = text(f"""
                    INSERT INTO catastro.predio (cod_catastral, posesionario_id, empresa_id, geom, area_ha, creado_por)
                    SELECT 
                        :codigo, :pos_id, :emp_id, 
                        ST_Force2D(ST_SetSRID(geom, 32717)),
                        ST_Area(ST_Force2D(ST_SetSRID(geom, 32717))) / 10000.0,
                        :creado_por
                    FROM {tabla_completa} WHERE id = :id_row
                    RETURNING id
                """)
                res_predio = db.execute(q_predio, {
                    "codigo": codigo_asignar,
                    "pos_id": posesionario_id,
                    "emp_id": empresa_id,
                    "id_row": fila['id'],
                    "creado_por": user_id
                }).mappings().first()
                
                if res_predio:
                    predio_id = res_predio["id"]
                    resultados["predios_creados"] += 1
                    
                    # 6.3 Topología: Vértices (Puntos)
                    q_vertices = text("""
                        INSERT INTO catastro.vertice (predio_id, cod_catastral, codigo, coord_x, coord_y, geom, empresa_id)
                        SELECT 
                            :predio_id, :codigo, 
                            'V' || LPAD(i::text, 2, '0'),
                            ST_X(ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i)),
                            ST_Y(ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i)),
                            ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i),
                            :emp_id
                        FROM catastro.predio
                        CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(geom, 1))) - 1) as i
                        WHERE id = :predio_id
                    """)
                    res_vert = db.execute(q_vertices, {"predio_id": predio_id, "codigo": codigo_asignar, "emp_id": empresa_id})
                    resultados["vertices_creados"] += res_vert.rowcount
                    
                    # 6.4 Topología: Linderos (Líneas)
                    q_lineas = text("""
                        INSERT INTO catastro.linea_lindero (predio_id, cod_catastral, longitud, colindante, geom, empresa_id)
                        SELECT 
                            :predio_id, :codigo, 
                            ST_Length(ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i+1))),
                            '',
                            ST_MakeLine(ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i), ST_PointN(ST_ExteriorRing(ST_GeometryN(geom, 1)), i+1)),
                            :emp_id
                        FROM catastro.predio
                        CROSS JOIN generate_series(1, ST_NumPoints(ST_ExteriorRing(ST_GeometryN(geom, 1))) - 1) as i
                        WHERE id = :predio_id
                    """)
                    res_lin = db.execute(q_lineas, {"predio_id": predio_id, "codigo": codigo_asignar, "emp_id": empresa_id})
                    resultados["lineas_creadas"] += res_lin.rowcount
            except Exception as row_err:
                logging.error(f"Error procesando fila {fila['id']} del shapefile: {row_err}")
                continue
                
        # Eliminar tabla temporal al finalizar Catastro Base
        db.execute(text(f"DROP TABLE {tabla_completa} CASCADE"))
        db.commit()
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
