import os
import glob
import time
import math
import shutil
import re
import shapefile
from shapely.geometry import shape, Polygon, MultiPolygon
from shapely import make_valid, STRtree
from shapely.ops import polygonize, unary_union

FOLDER = r"C:\LNCZ\proyecto-catastro-2026\SHAPE_ATLAS\Shapes_General"
PRJ_CONTENT = 'PROJCS["WGS_1984_UTM_Zone_17S",GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",10000000.0],PARAMETER["Central_Meridian",-81.0],PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'

def normalize_field_name(name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_').upper()[:10]
    clean = re.sub(r'_+', '_', clean)
    if clean in ['CLAVE_CATA', 'CODIGO', 'COD_CAT']:
        return 'COD_CAT'
    return clean or "FIELD"

def clean_cadastral_code(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    if s in ['0', 'None', '', 'S/C']:
        return ""
    if 'e+' in s.lower():
        try:
            s = f"{int(float(s))}"
        except Exception:
            pass
    if len(s) == 18 and s.startswith('206'):
        s = '1' + s
    return s[:30]

def clean_cedula_ruc(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    digits = re.sub(r'\D', '', s)
    if not digits:
        return ""
    # En Ecuador, cédulas de 9 dígitos provienen de números donde se omitió el 0 inicial
    if len(digits) == 9:
        digits = "0" + digits
    return digits[:13]

def extract_cedula_from_text(text):
    if not text:
        return ""
    s = str(text).strip()
    # Patrones explícitos: C.C. 1202292304, C.I: 1201563671, C.C: 1206292516, etc.
    m = re.search(r'(?:C[\.\s]*[CI][\.\s:]*|C[\.\s]*C[\.\s:]*|CED[\.\s:]*|RUC[\.\s:]*)(\d{9,13})', s, re.I)
    if m:
        return clean_cedula_ruc(m.group(1))
    m2 = re.search(r'\b(\d{9,10})\b', s)
    if m2:
        return clean_cedula_ruc(m2.group(1))
    return ""

def clean_place_name(text):
    if not text:
        return ""
    s = str(text).strip()
    s = re.sub(r'^(NULL|0|N/A|\.)+', '', s, flags=re.I).strip()
    if s.upper() == 'R0BLECITO':
        s = 'ROBLECITO'
    return s

def extract_sector_from_datos(datos):
    if not datos:
        return ""
    s = str(datos).strip()
    m = re.search(r'(?:SEC[\.:\s]+|SECTOR[\.:\s]+)(.+)$', s, re.I)
    if m:
        sec = m.group(1).strip(' .')
        sec = re.sub(r'(?:C[\.\s]*[CI][\.\s:]*|C[\.\s]*C[\.\s:]*|CED[\.\s:]*|RUC[\.\s:]*)\s*\d+.*', '', sec, flags=re.I).strip(' .')
        return sec
    s_clean = s.strip(' .')
    if s_clean.upper().startswith('SEC '):
        return s_clean[4:].strip(' .')
    return ""

def extract_name_from_datos(datos):
    if not datos:
        return ""
    s = str(datos).strip()
    clean = re.sub(r'(?:C[\.\s]*[CI][\.\s:]*|C[\.\s]*C[\.\s:]*|CED[\.\s:]*|RUC[\.\s:]*)\s*\d+.*', '', s, flags=re.I)
    clean = re.sub(r'(?:SEC[\.:\s]+|SECTOR[\.:\s]+).*', '', clean, flags=re.I).strip(' .')
    clean = re.sub(r'\b(MVD|MDV)\b', '', clean, flags=re.I).strip(' .')
    words = clean.split()
    if len(words) >= 2 and not any(w.upper() in ['SEC', 'SECTOR', 'RECINTO', 'LOTES', 'EL', 'LA', 'LOS', 'LAS'] and len(words) == 2 for w in words):
        return clean
    return ""

def get_unified_fields_map(files):
    field_defs = {}
    file_fields = {}
    
    for f in files:
        sf = shapefile.Reader(f)
        file_fields[f] = []
        for field in sf.fields[1:]:
            fn, ft, fl, fd = field
            norm = normalize_field_name(fn)
            file_fields[f].append((fn, norm, ft, fl, fd))
            if norm not in field_defs:
                field_defs[norm] = [ft, fl, fd]
            else:
                curr_t, curr_l, curr_d = field_defs[norm]
                if curr_t != ft:
                    curr_t = 'C'
                field_defs[norm] = [curr_t, max(curr_l, fl), max(curr_d, fd)]
        sf.close()
        
    return field_defs, file_fields

def clean_record_val(val, target_type):
    if val is None:
        return "" if target_type == 'C' else (0 if target_type == 'N' else None)
    if target_type == 'C':
        return str(val).strip()
    if target_type in ['N', 'F']:
        if isinstance(val, (int, float)):
            return val
        try:
            return float(str(val).replace(',', '.'))
        except Exception:
            return 0
    return val

def standardize_record_dict(rec_dict):
    """
    Aplica las reglas de negocio del usuario:
    1. Cédulas a CED_RUC con anteposición de '0' si son 9 dígitos, extrayendo de DATOS y CEDULA.
    2. Unión de NOMBRES y APELLIDOS.
    3. Consolidación de RECINTO y RECT en SECTOR sin duplicar.
    4. Unificación de CLAVE_CATA, CODIGO y COD_CAT en COD_CAT.
    """
    # 0. Código Catastral -> COD_CAT
    curr_cod = clean_cadastral_code(rec_dict.get('COD_CAT'))
    if curr_cod:
        rec_dict['COD_CAT'] = curr_cod

    # 1. Cédula / RUC
    curr_ced_ruc = clean_cedula_ruc(rec_dict.get('CED_RUC'))
    cand_ced = curr_ced_ruc
    if not cand_ced:
        cand_ced = clean_cedula_ruc(rec_dict.get('CEDULA'))
    if not cand_ced:
        cand_ced = clean_cedula_ruc(rec_dict.get('CDI_RUC')) or clean_cedula_ruc(rec_dict.get('CDE_RUC'))
    if not cand_ced:
        cand_ced = clean_cedula_ruc(rec_dict.get('NUMERO_IDE')) or clean_cedula_ruc(rec_dict.get('NUMERO_I_1'))
    if not cand_ced:
        cand_ced = extract_cedula_from_text(rec_dict.get('DATOS'))
        
    if cand_ced:
        rec_dict['CED_RUC'] = cand_ced
        
    # 2. Nombres y Apellidos
    nom = str(rec_dict.get('NOMBRES', '') or '').strip()
    apel = str(rec_dict.get('APELLIDOS', '') or '').strip()
    nom_pro = str(rec_dict.get('NOMBRE_PRO', '') or '').strip()
    
    full_name = nom
    if nom and apel:
        if apel.upper() not in nom.upper():
            full_name = f"{nom} {apel}".strip()
    elif not nom and apel:
        full_name = apel
        
    if not full_name:
        if nom_pro:
            full_name = nom_pro
        else:
            ext_name = extract_name_from_datos(rec_dict.get('DATOS'))
            if ext_name:
                full_name = ext_name
                
    if full_name:
        rec_dict['NOMBRES'] = full_name
        if not nom_pro:
            rec_dict['NOMBRE_PRO'] = full_name

    # 3. Recinto / Rect -> Agregar a Sector sin duplicar
    sec = clean_place_name(rec_dict.get('SECTOR'))
    rec = clean_place_name(rec_dict.get('RECINTO'))
    rect = clean_place_name(rec_dict.get('RECT'))
    
    if rect and any(k in rect.upper() for k in ['BASANTES', 'QUIÑONEZ']):
        rect = ''
        
    cand_lugar = rec or rect
    datos_sec = extract_sector_from_datos(rec_dict.get('DATOS'))
    
    final_sec = sec
    if not final_sec:
        final_sec = cand_lugar or datos_sec
    else:
        addon = cand_lugar or datos_sec
        if addon:
            addon_u = addon.upper()
            sec_u = final_sec.upper()
            if addon_u not in sec_u and sec_u not in addon_u:
                final_sec = f"{final_sec} / {addon}"
                
    if final_sec:
        rec_dict['SECTOR'] = final_sec

def process_unification(files, output_path, is_predios=False):
    t0 = time.time()
    out_name = os.path.basename(output_path)
    print(f"\n=======================================================")
    print(f" Procesando: {out_name}")
    print(f" Total fuentes: {len(files)}")
    print(f"=======================================================")
    
    field_defs, file_fields = get_unified_fields_map(files)
    field_defs["ORIGEN_SHP"] = ['C', 45, 0]
    
    # Asegurar que CED_RUC sea de tipo C (texto) y longitud suficiente para no perder ceros
    if "CED_RUC" in field_defs:
        field_defs["CED_RUC"] = ['C', 15, 0]
    else:
        field_defs["CED_RUC"] = ['C', 15, 0]

    # Unificar código catastral en COD_CAT (texto 30)
    field_defs["COD_CAT"] = ['C', 30, 0]
        
    if "NOMBRES" in field_defs:
        field_defs["NOMBRES"] = ['C', 200, 0]
    if "NOMBRE_PRO" in field_defs:
        field_defs["NOMBRE_PRO"] = ['C', 250, 0]
    if "SECTOR" in field_defs:
        field_defs["SECTOR"] = ['C', 200, 0]
        
    all_col_names = sorted(list(field_defs.keys()))

    accepted_geoms = []
    accepted_records = []
    
    total_raw = 0
    dups_count = 0
    overlap_count = 0
    errors_count = 0
    line_poly_count = 0
    
    if is_predios:
        files = sorted(files, key=lambda f: os.path.getsize(f), reverse=True)
        
    for file_idx, fpath in enumerate(files):
        fname = os.path.basename(fpath)
        sf = shapefile.Reader(fpath)
        orig_fields = [f[0] for f in sf.fields[1:]]
        norm_fields = [normalize_field_name(fn) for fn in orig_fields]
        is_line_file = 'LINE' in sf.shapeTypeName.upper()
        
        recs = sf.records()
        shapes = sf.shapes()
        total_raw += len(shapes)
        
        print(f"[{file_idx+1}/{len(files)}] {fname} ({sf.shapeTypeName}, {len(shapes)} elementos)")
        
        if is_line_file:
            lines = []
            line_recs = []
            for s, r in zip(shapes, recs):
                try:
                    g = shape(s.__geo_interface__)
                    if g.is_valid and not g.is_empty:
                        lines.append(g)
                        line_recs.append(r)
                except Exception:
                    pass
            if lines:
                merged = unary_union(lines)
                formed_polys = list(polygonize(merged))
                line_poly_count += len(formed_polys)
                
                lines_tree = STRtree(lines)
                tree = STRtree(accepted_geoms) if accepted_geoms else None
                for poly in formed_polys:
                    if not poly.is_valid:
                        poly = make_valid(poly)
                    if poly.is_empty or poly.area < 1.0:
                        continue
                    
                    is_dup = False
                    is_overlap = False
                    if tree is not None:
                        cands = tree.query(poly)
                        for c_idx in cands:
                            ex = accepted_geoms[c_idx]
                            if poly.equals(ex):
                                is_dup = True
                                break
                            inter = poly.intersection(ex)
                            if inter.area > 5.0 and (inter.area / poly.area > 0.1 or inter.area / ex.area > 0.1):
                                is_overlap = True
                                break
                    if is_dup:
                        dups_count += 1
                        continue
                    if is_overlap:
                        overlap_count += 1
                        continue
                        
                    cand_lines = lines_tree.query(poly.boundary)
                    chosen_rec = None
                    for cl_idx in cand_lines:
                        if lines[cl_idx].intersects(poly.boundary):
                            chosen_rec = line_recs[cl_idx]
                            break
                    if chosen_rec is None and len(line_recs) > 0:
                        chosen_rec = line_recs[0]
                        
                    rec_dict = {}
                    if chosen_rec:
                        for nf, val in zip(norm_fields, chosen_rec):
                            rec_dict[nf] = val
                    rec_dict["ORIGEN_SHP"] = fname[:45]
                    
                    if is_predios:
                        standardize_record_dict(rec_dict)
                        
                    row = [clean_record_val(rec_dict.get(col), field_defs[col][0]) for col in all_col_names]
                    accepted_geoms.append(poly)
                    accepted_records.append(row)
        else:
            tree = STRtree(accepted_geoms) if accepted_geoms else None
            for s, r in zip(shapes, recs):
                try:
                    pts = s.points
                    if not pts or len(pts) < 3:
                        continue
                    has_nan = any(math.isnan(p[0]) or math.isnan(p[1]) or math.isinf(p[0]) or math.isinf(p[1]) for p in pts)
                    if has_nan:
                        errors_count += 1
                        continue
                        
                    g = shape(s.__geo_interface__)
                    if not g.is_valid:
                        g = make_valid(g)
                    if hasattr(g, 'geoms') and g.geom_type == 'GeometryCollection':
                        polys = [p for p in g.geoms if p.geom_type in ['Polygon', 'MultiPolygon']]
                        if polys:
                            g = unary_union(polys)
                        else:
                            continue
                            
                    min_area = 1.0 if is_predios else 0.05
                    if g.is_empty or g.area < min_area:
                        continue
                        
                    is_dup = False
                    is_overlap = False
                    if tree is not None:
                        cands = tree.query(g)
                        for c_idx in cands:
                            ex = accepted_geoms[c_idx]
                            if g.equals(ex):
                                is_dup = True
                                break
                            inter = g.intersection(ex)
                            overlap_threshold = 5.0 if is_predios else 1.0
                            ratio_threshold = 0.1 if is_predios else 0.05
                            if inter.area > overlap_threshold and (inter.area / g.area > ratio_threshold or inter.area / ex.area > ratio_threshold):
                                is_overlap = True
                                break
                    if is_dup:
                        dups_count += 1
                        continue
                    if is_overlap:
                        overlap_count += 1
                        continue
                        
                    rec_dict = {nf: val for nf, val in zip(norm_fields, r)}
                    rec_dict["ORIGEN_SHP"] = fname[:45]
                    
                    if is_predios:
                        standardize_record_dict(rec_dict)
                        
                    row = [clean_record_val(rec_dict.get(col), field_defs[col][0]) for col in all_col_names]
                    accepted_geoms.append(g)
                    accepted_records.append(row)
                except Exception as e:
                    errors_count += 1
                    
        sf.close()

    print(f"\nGuardando {len(accepted_geoms)} poligonos limpios en: {output_path}...")
    
    w = shapefile.Writer(output_path, shapeType=shapefile.POLYGON)
    for col in all_col_names:
        ftype, flen, fdec = field_defs[col]
        flen = min(flen, 254)
        if ftype == 'C' and flen < 1:
            flen = 80
        w.field(col, ftype, flen, fdec)
        
    for g, row in zip(accepted_geoms, accepted_records):
        w.shape(g.__geo_interface__)
        w.record(*row)
        
    w.close()
    
    base_no_ext = os.path.splitext(output_path)[0]
    with open(base_no_ext + ".prj", "w", encoding="utf-8") as f:
        f.write(PRJ_CONTENT)
    with open(base_no_ext + ".cpg", "w", encoding="utf-8") as f:
        f.write("UTF-8")
        
    dur = time.time() - t0
    print(f"=== RESULTADOS DE {out_name} ===")
    print(f"  * Elementos procesados (entrada): {total_raw}")
    if line_poly_count > 0:
        print(f"  * Poligonos generados de lineas: {line_poly_count}")
    print(f"  * Elementos finales ACEPTADOS:   {len(accepted_geoms)}")
    print(f"  * Descartados por DUPLICADOS:     {dups_count}")
    print(f"  * Descartados por SOBREPOSICION:  {overlap_count}")
    print(f"  * Omitidos por error o vacios:    {errors_count}")
    print(f"  * Tiempo total de ejecucion:     {dur:.2f} s")
    print(f"=======================================================\n")

def main():
    all_files = sorted(glob.glob(os.path.join(FOLDER, "*.shp")))
    
    c_names = set([
        os.path.basename(f) for f in all_files 
        if os.path.basename(f).upper().startswith('CONSTRUCC') or 
           os.path.basename(f).upper() in ['CONST.SHP', 'POLI_CONSTRUCCION.SHP', 'UNIFICACION.SHP', 'CONSTRUCCIONES_SHAPES.SHP', 'UNIFICACION_CLEANED.SHP']
    ])
    
    predios_files = [
        f for f in all_files 
        if os.path.basename(f) not in c_names and not os.path.basename(f).upper().startswith('UNIFICACION')
    ]
    
    # Procesar Predios / Polígonos con todas las normalizaciones de atributos solicitadas
    out_norm = os.path.join(FOLDER, "Unificacion_Normalizado.shp")
    process_unification(predios_files, out_norm, is_predios=True)
    
    # Intentar reemplazar Unificacion.shp si no está bloqueado por ArcMap
    out_orig = os.path.join(FOLDER, "Unificacion.shp")
    reemplazado = False
    try:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            orig_f = os.path.splitext(out_orig)[0] + ext
            norm_f = os.path.splitext(out_norm)[0] + ext
            if os.path.exists(orig_f):
                os.remove(orig_f)
            shutil.copy2(norm_f, orig_f)
        reemplazado = True
        print("\n-> ¡'Unificacion.shp' fue actualizado y sobreescrito exitosamente!")
    except Exception as e:
        print(f"\n-> Nota: 'Unificacion.shp' está en uso por ArcMap/QGIS ({e}).")
        print("-> Se guardó la versión completa actualizada en: 'Unificacion_Normalizado.shp'")

if __name__ == "__main__":
    main()
