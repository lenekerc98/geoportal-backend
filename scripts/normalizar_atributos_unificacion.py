import os
import re
import shapefile
import time

FOLDER = r"C:\LNCZ\proyecto-catastro-2026\SHAPE_ATLAS\Shapes_General"
INPUT_SHP = os.path.join(FOLDER, "Unificacion.shp")
TEMP_SHP = os.path.join(FOLDER, "Unificacion_cleaned.shp")

def clean_cedula_ruc(val):
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith('.0'):
        s = s[:-2]
    digits = re.sub(r'\D', '', s)
    if not digits:
        return ""
    # Si tiene 9 dígitos, en Ecuador se le antepone el 0
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
    # Número aislado de 9 o 10 dígitos
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
    # Buscar patrón de sector: SEC., SEC:, SEC, SECTOR
    m = re.search(r'(?:SEC[\.:\s]+|SECTOR[\.:\s]+)(.+)$', s, re.I)
    if m:
        sec = m.group(1).strip(' .')
        # Limpiar si al final viene C.C.
        sec = re.sub(r'(?:C[\.\s]*[CI][\.\s:]*|C[\.\s]*C[\.\s:]*|CED[\.\s:]*|RUC[\.\s:]*)\s*\d+.*', '', sec, flags=re.I).strip(' .')
        return sec
    # Si todo el texto es un sector conocido como 'SEC POTOSI' o '. LA ASUNCION'
    s_clean = s.strip(' .')
    if s_clean.upper().startswith('SEC '):
        return s_clean[4:].strip(' .')
    return ""

def extract_name_from_datos(datos):
    if not datos:
        return ""
    s = str(datos).strip()
    # Eliminar sección de Cédula y de Sector
    clean = re.sub(r'(?:C[\.\s]*[CI][\.\s:]*|C[\.\s]*C[\.\s:]*|CED[\.\s:]*|RUC[\.\s:]*)\s*\d+.*', '', s, flags=re.I)
    clean = re.sub(r'(?:SEC[\.:\s]+|SECTOR[\.:\s]+).*', '', clean, flags=re.I).strip(' .')
    # Quitar posibles sufijos MVD o MDV
    clean = re.sub(r'\b(MVD|MDV)\b', '', clean, flags=re.I).strip(' .')
    words = clean.split()
    if len(words) >= 2 and not any(w.upper() in ['SEC', 'SECTOR', 'RECINTO', 'LOTES', 'EL', 'LA', 'LOS', 'LAS'] and len(words) == 2 for w in words):
        return clean
    return ""

def main():
    t0 = time.time()
    print("Abriendo Unificacion.shp para estandarizar atributos...")
    
    sf = shapefile.Reader(INPUT_SHP)
    fields = sf.fields[1:]
    col_names = [f[0] for f in fields]
    
    total_recs = len(sf)
    print(f"Total registros a procesar: {total_recs}")
    
    # Índices de columnas clave
    idx_ced_ruc = col_names.index('CED_RUC') if 'CED_RUC' in col_names else None
    idx_cedula = col_names.index('CEDULA') if 'CEDULA' in col_names else None
    idx_datos = col_names.index('DATOS') if 'DATOS' in col_names else None
    idx_nombres = col_names.index('NOMBRES') if 'NOMBRES' in col_names else None
    idx_apellidos = col_names.index('APELLIDOS') if 'APELLIDOS' in col_names else None
    idx_nom_pro = col_names.index('NOMBRE_PRO') if 'NOMBRE_PRO' in col_names else None
    idx_recinto = col_names.index('RECINTO') if 'RECINTO' in col_names else None
    idx_rect = col_names.index('RECT') if 'RECT' in col_names else None
    idx_sector = col_names.index('SECTOR') if 'SECTOR' in col_names else None
    
    # Métricas
    ced_antes = sum(1 for r in sf.records() if str(r[idx_ced_ruc]).strip() not in ['', 'None', '0'])
    sec_antes = sum(1 for r in sf.records() if str(r[idx_sector]).strip() not in ['', 'None'])
    nom_unidos = 0
    ced_despues = 0
    sec_despues = 0
    
    # Preparar nuevo shapefile
    w = shapefile.Writer(TEMP_SHP, shapeType=shapefile.POLYGON)
    for f in fields:
        fname, ftype, flen, fdec = f
        flen = min(flen, 254)
        if ftype == 'C' and flen < 1:
            flen = 80
        # Asegurar longitud amplia para campos combinados
        if fname in ['CED_RUC', 'CEDULA'] and ftype == 'C':
            flen = max(flen, 15)
        if fname in ['NOMBRES', 'NOMBRE_PRO', 'SECTOR'] and ftype == 'C':
            flen = max(flen, 200)
        w.field(fname, ftype, flen, fdec)
        
    for idx in range(total_recs):
        sh = sf.shape(idx)
        r = list(sf.record(idx))
        d = dict(zip(col_names, r))
        
        # 1. Cédula / RUC -> CED_RUC
        curr_ced_ruc = clean_cedula_ruc(d.get('CED_RUC'))
        cand_ced = curr_ced_ruc
        if not cand_ced:
            cand_ced = clean_cedula_ruc(d.get('CEDULA'))
        if not cand_ced:
            cand_ced = clean_cedula_ruc(d.get('CDI_RUC')) or clean_cedula_ruc(d.get('CDE_RUC'))
        if not cand_ced:
            cand_ced = clean_cedula_ruc(d.get('NUMERO_IDE')) or clean_cedula_ruc(d.get('NUMERO_I_1'))
        if not cand_ced:
            cand_ced = extract_cedula_from_text(d.get('DATOS'))
            
        if cand_ced:
            ced_despues += 1
            if idx_ced_ruc is not None:
                r[idx_ced_ruc] = cand_ced
                
        # 2. Nombres y Apellidos -> Unirlos
        nom = str(d.get('NOMBRES', '') or '').strip()
        apel = str(d.get('APELLIDOS', '') or '').strip()
        nom_pro = str(d.get('NOMBRE_PRO', '') or '').strip()
        
        full_name = nom
        if nom and apel:
            # Si el apellido no está ya incluido en nombres, unirlos
            if apel.upper() not in nom.upper():
                full_name = f"{nom} {apel}".strip()
                nom_unidos += 1
        elif not nom and apel:
            full_name = apel
            
        # Si sigue vacío, buscar en NOMBRE_PRO o extraer de DATOS
        if not full_name:
            if nom_pro:
                full_name = nom_pro
            else:
                extracted_name = extract_name_from_datos(d.get('DATOS'))
                if extracted_name:
                    full_name = extracted_name
                    
        # Actualizar en el registro
        if full_name:
            if idx_nombres is not None:
                r[idx_nombres] = full_name[:200]
            if idx_nom_pro is not None and not str(r[idx_nom_pro]).strip():
                r[idx_nom_pro] = full_name[:200]
                
        # 3. Recinto / Rect -> Agregar a Sector sin duplicar
        curr_sec = clean_place_name(d.get('SECTOR'))
        rec = clean_place_name(d.get('RECINTO'))
        rect = clean_place_name(d.get('RECT'))
        
        # Omitir si RECT es accidentalmente un nombre de persona
        if rect and any(k in rect.upper() for k in ['BASANTES', 'QUIÑONEZ']):
            rect = ''
            
        cand_lugar = rec or rect
        datos_sec = extract_sector_from_datos(d.get('DATOS'))
        
        final_sec = curr_sec
        if not final_sec:
            final_sec = cand_lugar or datos_sec
        else:
            # Si ya tiene sector, pero viene otro recinto que no está repetido
            addon = cand_lugar or datos_sec
            if addon:
                addon_clean = addon.upper()
                sec_clean = final_sec.upper()
                if addon_clean not in sec_clean and sec_clean not in addon_clean:
                    final_sec = f"{final_sec} / {addon}"
                    
        if final_sec:
            sec_despues += 1
            if idx_sector is not None:
                r[idx_sector] = final_sec[:200]
                
        w.shape(sh.__geo_interface__)
        w.record(*r)
        
    w.close()
    sf.close()
    
    # Reemplazar archivo original
    base_no_ext = os.path.splitext(INPUT_SHP)[0]
    for ext in ['.shp', '.shx', '.dbf']:
        orig_file = base_no_ext + ext
        temp_file = os.path.splitext(TEMP_SHP)[0] + ext
        if os.path.exists(orig_file):
            os.remove(orig_file)
        os.rename(temp_file, orig_file)
        
    print("\n=======================================================")
    print(" ESTANDARIZACIÓN COMPLETADA CON ÉXITO")
    print("=======================================================")
    print(f"  * Cédula / RUC (CED_RUC):")
    print(f"      Antes con valor:    {ced_antes}")
    print(f"      Ahora con valor:    {ced_despues} (con formato a 10 dígitos y '0' inicial si eran 9)")
    print(f"  * Nombres y Apellidos:")
    print(f"      Pares unificados:   {nom_unidos} (unidos en NOMBRES y NOMBRE_PRO)")
    print(f"  * Sector (SECTOR + RECINTO + RECT + DATOS):")
    print(f"      Antes con valor:    {sec_antes}")
    print(f"      Ahora con valor:    {sec_despues} (sin duplicar nombres idénticos)")
    print(f"  * Tiempo transcurrido:  {time.time()-t0:.2f} s")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
