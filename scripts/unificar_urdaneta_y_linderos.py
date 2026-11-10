# -*- coding: utf-8 -*-
"""
========================================================================================
CATASTRO 2026 - UNIFICADOR ESPACIAL DE POLÍGONOS, TEXTOS INTERNOS Y LINDEROS (URDANETA)
========================================================================================
Toma los shapefiles en C:\LNCZ\proyecto-catastro-2026\Shapes_carga\SHAPE_URDANETA_DOS\transformar:
  - Polígonos: POLIGONO_00.zip + POLIGONO_01.zip
  - Textos CAD: NOMBRES_0.zip + NOMBRES_01.zip

Genera en .../transformar/SALIDA_UNIFICADA/:
  1. PREDIOS_URDANETA_UNIFICADO.zip
     Incluye .shp/.shx/.dbf/.prj/.cpg + predios_metadata_completa.json (sin truncado 254 bytes)
  2. LINDEROS_URDANETA_UNIFICADO.zip
     Capa de líneas con tramo, rumbo, longitud, orientación y colindante de cada lado
  3. NOMBRES_URDANETA_UNIFICADO.zip
     Capa unificada y deduplicada de puntos de texto con EPSG:32717
  4. REPORTE_UNIFICACION.csv
     Auditoría tabular para revisión rápida en Excel
========================================================================================
"""

import os
import io
import re
import csv
import json
import math
import time
import warnings
import zipfile
from typing import List, Dict, Any, Tuple, Optional

import shapefile
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon
from shapely.ops import orient, substring
from shapely import make_valid, STRtree

warnings.filterwarnings("ignore", message=".*Shapefile format requires.*")

INPUT_DIR = r"C:\LNCZ\proyecto-catastro-2026\Shapes_carga\SHAPE_URDANETA_DOS\transformar"
OUTPUT_DIR = os.path.join(INPUT_DIR, "SALIDA_UNIFICADA")

PRJ_EPSG_32717 = (
    'PROJCS["WGS_1984_UTM_Zone_17S",GEOGCS["GCS_WGS_1984",'
    'DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],'
    'PARAMETER["False_Northing",10000000.0],PARAMETER["Central_Meridian",-81.0],'
    'PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
)

KNOWN_SECTORS = {
    "POTOSI", "RICAURTE", "RICAURET", "CATARAMA", "PIJULLO", "SAN ANTONIO", "SAN NICOLAS",
    "LA DOLOROSA", "COOP. LA DOLOROSA", "LAS CASITAS", "RCTO. LAS CASITAS",
    "POMPEYA", "LA POMPEYA", "CASTILLO", "CERRITOS", "LOS CERRITOS", "LA HOJITA", "LA IRENE",
    "MONSERRATE", "SANTA CLARA", "ROBLECITO", "CHUMBO BAJAÑA", "LA FLORENCIA",
    "EL EDEN", "LA CAROLINA", "LA SALINA", "SALINA", "EL CARMEN", "LA UNION",
    "SAN JOSE", "SAN VICENTE", "CAÑITAS", "OJIVO", "VILLA CEDEÑO", "EL LIMON",
    "LOS LIMOS", "LA FORTUNA", "LA VICTORIA", "PUERTO PECHICHE", "ESTERO CLARO",
    "EL GUAYABO", "MONTE CARLOS", "YATIVI", "GUYACANES", "GUAYACANES", "HORNACHO"
}

RE_NUMBER_LOC = r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?'

RE_AREA_LINE = re.compile(
    rf'^(?:(?:ÁREA|AREA|SUP\.?|SUPERFICIE)\s*[:.]?\s*)?(?:{RE_NUMBER_LOC})\s*(?:MTS?2?\.?|M2|M²|HAS?\.?|HECTAREAS?|CDRAS?\.?|CUADRAS?|MZ\.?)\s*\.?$',
    re.IGNORECASE
)
RE_AREA_ANY = re.compile(
    rf'\b(?:{RE_NUMBER_LOC})\s*(?:MTS2|MTS\.?2|M2|M²|HAS\.?|HECTAREAS?|CDRAS?\.?|CUADRAS?)\b',
    re.IGNORECASE
)
RE_MEASURE_ONLY = re.compile(
    rf'^(?:{RE_NUMBER_LOC})\s*(?:m\.?|mts?\.?|metros?)?$',
    re.IGNORECASE
)
RE_RUMBO_TEXT = re.compile(r'^[NS]\s+\d+\s*[°º]\s*\d+\s*[\'’]\s*\d+(?:[.,]\d+)?\s*["”]?\s*[EWO]$', re.IGNORECASE)
RE_CURRENCY_TEXT = re.compile(r'^\$?\s*(?:{RE_NUMBER_LOC})\s*D[ÓO]LARES?$|^\$\s*(?:{RE_NUMBER_LOC})', re.IGNORECASE)
RE_CAD_ADMIN_OR_CROP = re.compile(
    r'^(?:PROVINCIA\s*:|CANT[ÓO]N\s*:|PARROQUIA\s*:|JUICIO\b|APROBAD|A[ÑN]O\s*:|ESCALA\s*:|FECHA\s*:|CACAO|MANGO|BANANO|ARROZ|MA[ÍI]Z|SOYA|POTRERO|PASTIZAL)\b',
    re.IGNORECASE
)
RE_SOLAR_LOTE = re.compile(
    r'^(?:SOLAR|LOTE|PARCELA|MZ\.?|MANZANA|FINCA|HACIENDA|HCDA\.?|PREDIO)\b',
    re.IGNORECASE
)
RE_SECTOR_PREFIX = re.compile(
    r'^(?:SEC\.?|SECTOR|RCTO\.?|RECINTO|COOP\.?|COOPERATIVA|COMUNA|BARRIO|CDLA\.?|CIUDADELA)\b[:.\s]*',
    re.IGNORECASE
)
RE_ROAD_OR_WATER = re.compile(
    r'\b(?:CALLE|CAMINO|CARRETERO|VIA|V[ÍI]A|AVENIDA|AV\.|CALLEJ[ÓO]N|PASO|ESTERO|R[ÍI]O|RIO|CANAL|QUEBRADA|ACEQUIA|ZANJA|GUARDARRAYA)\b',
    re.IGNORECASE
)
RE_CEDULA = re.compile(r'(?:C\.?\s*C\.?|C\.?\s*I\.?|CEDULA|RUC)?\s*[:.]?\s*(\d{9,13})\b', re.IGNORECASE)
RE_VERTEX_OR_NOISE = re.compile(r'^(?:\d{1,3}|[A-Z]|R[ÓO]TULO|ROTULO|NULL|S/N|S/D|N/A|---|\.+)$', re.IGNORECASE)
RE_DANGLING_KEYWORD = re.compile(r'^(?:PROPIETARIO|POSESIONARIO|PREDIO|SECTOR|SEC|RECINTO|PARROQUIA|CANTON|PROVINCIA|AREA|ÁREA)\s*:?$', re.IGNORECASE)


def decode_smart(raw_val: Any) -> str:
    """Decodifica cadenas DBF mezcladas UTF-8 / CP1252 sin generar caracteres corruptos."""
    if raw_val is None:
        return ""
    if isinstance(raw_val, bytes):
        raw_bytes = raw_val
    else:
        raw_bytes = str(raw_val).encode("latin1", errors="replace")
    try:
        txt = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        txt = raw_bytes.decode("cp1252", errors="replace")
    return re.sub(r'\s+', ' ', txt).strip()


def truncate_utf8(text: str, max_bytes: int) -> str:
    """Trunca exactamente por longitud de bytes UTF-8 para evitar PossibleDataLoss en Shapefile DBF."""
    if not text:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore").rstrip()


def compact_key(text: str) -> str:
    """Normaliza espacios para detectar duplicados tipo 'ELSA ANALUIZA' vs 'E L S A  A N A L U I Z A'."""
    return re.sub(r'\s+', '', (text or "").upper())


def utm17s_to_wgs84(x: float, y: float) -> Tuple[float, float]:
    """Conversión precisa UTM Zona 17S (WGS84) a (lng, lat)."""
    a = 6378137.0
    f = 1.0 / 298.257223563
    e2 = f * (2.0 - f)
    ep2 = e2 / (1.0 - e2)
    k0 = 0.9996
    lon0 = math.radians(-81.0)

    x_adj = x - 500000.0
    y_adj = y - 10000000.0

    m = y_adj / k0
    mu = m / (a * (1.0 - e2 / 4.0 - 3.0 * e2 * e2 / 64.0 - 5.0 * (e2 ** 3) / 256.0))
    e1 = (1.0 - math.sqrt(1.0 - e2)) / (1.0 + math.sqrt(1.0 - e2))

    j1 = 3.0 * e1 / 2.0 - 27.0 * (e1 ** 3) / 32.0
    j2 = 21.0 * (e1 ** 2) / 16.0 - 55.0 * (e1 ** 4) / 32.0
    j3 = 151.0 * (e1 ** 3) / 96.0
    j4 = 1097.0 * (e1 ** 4) / 512.0

    fp = mu + j1 * math.sin(2.0 * mu) + j2 * math.sin(4.0 * mu) + j3 * math.sin(6.0 * mu) + j4 * math.sin(8.0 * mu)
    sin_fp = math.sin(fp)
    cos_fp = math.cos(fp)
    tan_fp = math.tan(fp)

    c1 = ep2 * (cos_fp ** 2)
    t1 = tan_fp ** 2
    r1 = a * (1.0 - e2) / ((1.0 - e2 * (sin_fp ** 2)) ** 1.5)
    n1 = a / math.sqrt(1.0 - e2 * (sin_fp ** 2))
    d = x_adj / (n1 * k0)

    lat = fp - (n1 * tan_fp / r1) * (
        (d ** 2) / 2.0
        - (5.0 + 3.0 * t1 + 10.0 * c1 - 4.0 * (c1 ** 2) - 9.0 * ep2) * (d ** 4) / 24.0
        + (61.0 + 90.0 * t1 + 298.0 * c1 + 45.0 * (t1 ** 2) - 252.0 * ep2 - 3.0 * (c1 ** 2)) * (d ** 6) / 720.0
    )
    lon = lon0 + (
        d
        - (1.0 + 2.0 * t1 + c1) * (d ** 3) / 6.0
        + (5.0 - 2.0 * c1 + 28.0 * t1 - 3.0 * (c1 ** 2) + 8.0 * ep2 + 24.0 * (t1 ** 2)) * (d ** 5) / 120.0
    ) / cos_fp
    return round(math.degrees(lon), 7), round(math.degrees(lat), 7)


def is_valid_utm_pt(x: float, y: float) -> bool:
    return math.isfinite(x) and math.isfinite(y) and 100000.0 <= x <= 900000.0 and 9000000.0 <= y <= 10100000.0


def extract_valid_polygons(geom) -> List[Polygon]:
    out: List[Polygon] = []
    if geom is None or geom.is_empty:
        return out
    if isinstance(geom, Polygon):
        polys = [geom]
    elif isinstance(geom, MultiPolygon):
        polys = list(geom.geoms)
    elif hasattr(geom, "geoms"):
        flat = []
        for g in geom.geoms:
            flat.extend(extract_valid_polygons(g))
        polys = flat
    else:
        return out

    for p in polys:
        if not p.is_valid:
            p = make_valid(p)
            if not isinstance(p, Polygon):
                out.extend(extract_valid_polygons(p))
                continue
        if p.is_empty or p.area < 1.0:
            continue
        coords = list(p.exterior.coords)
        if not all(is_valid_utm_pt(pt[0], pt[1]) for pt in coords):
            continue
        out.append(p)
    return out


def normalize_ring_cw_nw(poly: Polygon) -> Tuple[Polygon, List[Tuple[float, float]]]:
    """
    Reorienta el anillo exterior en sentido horario (CW) comenzando en P01 Noroeste (normY - normX),
    idéntico a procesar_topologia_predio().
    """
    poly_cw = orient(poly, sign=-1.0)
    raw = [(round(float(x), 3), round(float(y), 3)) for x, y, *_ in poly_cw.exterior.coords]
    if len(raw) < 4:
        return poly_cw, raw

    cleaned: List[Tuple[float, float]] = []
    for pt in raw[:-1]:
        if not cleaned or math.hypot(pt[0] - cleaned[-1][0], pt[1] - cleaned[-1][1]) >= 0.02:
            cleaned.append(pt)
    if len(cleaned) >= 3 and math.hypot(cleaned[0][0] - cleaned[-1][0], cleaned[0][1] - cleaned[-1][1]) < 0.02:
        cleaned.pop()
    if len(cleaned) < 3:
        return poly_cw, raw[:-1]

    min_x = min(c[0] for c in cleaned)
    max_x = max(c[0] for c in cleaned)
    min_y = min(c[1] for c in cleaned)
    max_y = max(c[1] for c in cleaned)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0

    best_idx = 0
    best_score = -float("inf")
    for idx, (x, y) in enumerate(cleaned):
        score = ((y - min_y) / span_y) - ((x - min_x) / span_x)
        if score > best_score + 1e-5:
            best_score = score
            best_idx = idx
        elif abs(score - best_score) <= 1e-5:
            bx, by = cleaned[best_idx]
            if y > by or (abs(y - by) <= 1e-5 and x < bx):
                best_idx = idx

    rotated = cleaned[best_idx:] + cleaned[:best_idx]
    holes = [[(round(float(x), 3), round(float(y), 3)) for x, y, *_ in interior.coords] for interior in poly_cw.interiors]
    new_poly = Polygon(rotated + [rotated[0]], holes)
    if not new_poly.is_valid:
        new_poly = make_valid(new_poly)
        if not isinstance(new_poly, Polygon):
            return orient(poly, sign=-1.0), rotated
    return new_poly, rotated


def calcular_rumbo_utm(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[str, float]:
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    if dist < 1e-9:
        return "N 0° 0' 0\" E", 0.0
    az_rad = math.atan2(dx, dy)
    if az_rad < 0:
        az_rad += 2.0 * math.pi
    az = math.degrees(az_rad)
    if 0 <= az <= 90:
        q, r = "NE", az
    elif 90 < az <= 180:
        q, r = "SE", 180.0 - az
    elif 180 < az <= 270:
        q, r = "SW", az - 180.0
    else:
        q, r = "NW", 360.0 - az
    d = int(math.floor(r))
    m = int(math.floor((r - d) * 60.0))
    s = round(((r - d) * 60.0 - m) * 60.0)
    if s >= 60:
        s = 0
        m += 1
    if m >= 60:
        m = 0
        d += 1
    return f"{q[0]} {d}° {m}' {s}\" {q[1]}", round(dist, 2)


def get_cardinal_orientations(coords: List[Tuple[float, float]]) -> List[str]:
    n = len(coords)
    if n < 3:
        return []
    if n == 3:
        return ["NORTE", "ESTE", "OESTE"]
    min_x = min(c[0] for c in coords)
    max_x = max(c[0] for c in coords)
    min_y = min(c[1] for c in coords)
    max_y = max(c[1] for c in coords)
    span_x = (max_x - min_x) or 1.0
    span_y = (max_y - min_y) or 1.0

    ne_idx, best_ne = 1, -float("inf")
    for i in range(1, max(1, n - 3) + 1):
        sc = ((coords[i][1] - min_y) / span_y) + ((coords[i][0] - min_x) / span_x)
        if sc > best_ne:
            best_ne, ne_idx = sc, i

    se_idx, best_se = min(n - 2, ne_idx + 1), -float("inf")
    for i in range(ne_idx + 1, max(min(n - 2, ne_idx + 1), n - 2) + 1):
        sc = -((coords[i][1] - min_y) / span_y) + ((coords[i][0] - min_x) / span_x)
        if sc > best_se:
            best_se, se_idx = sc, i

    sw_idx, best_sw = min(n - 1, se_idx + 1), -float("inf")
    for i in range(se_idx + 1, n):
        sc = -((coords[i][1] - min_y) / span_y) - ((coords[i][0] - min_x) / span_x)
        if sc > best_sw:
            best_sw, sw_idx = sc, i

    res = []
    for i in range(n):
        if i < ne_idx:
            res.append("NORTE")
        elif i < se_idx:
            res.append("ESTE")
        elif i < sw_idx:
            res.append("SUR")
        else:
            res.append("OESTE")
    return res


def normalize_cad_angle(val: Any) -> float:
    try:
        a = float(val)
        if not math.isfinite(a):
            return 0.0
        a = a % 360.0
        if abs(a - 360.0) < 0.01:
            return 0.0
        return round(a, 2)
    except Exception:
        return 0.0


def angle_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 360.0
    return min(d, 360.0 - d)


def group_cad_text_stacks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa puntos de texto CAD apilados en la misma columna/ángulo usando índice espacial STRtree O(n log n).
    """
    if not items:
        return []
    n = len(items)
    pts = [t["geom"] for t in items]
    tree = STRtree(pts)
    used = [False] * n
    blocks: List[Dict[str, Any]] = []

    for i in range(n):
        if used[i]:
            continue
        used[i] = True
        cluster = [items[i]]
        queue = [items[i]]
        while queue:
            cur = queue.pop(0)
            a_rad = math.radians(cur["angle"])
            along_u = (math.cos(a_rad), math.sin(a_rad))
            down_u = (math.sin(a_rad), -math.cos(a_rad))
            sz = float(cur.get("size") or 2.0)
            search_r = max(13.0, 5.0 * sz)

            for j in tree.query(cur["geom"].buffer(search_r)):
                if used[j]:
                    continue
                cand = items[j]
                if angle_diff_deg(cur["angle"], cand["angle"]) > 10.0:
                    continue
                dx = cand["x"] - cur["x"]
                dy = cand["y"] - cur["y"]
                d_along = abs(dx * along_u[0] + dy * along_u[1])
                d_perp = abs(dx * down_u[0] + dy * down_u[1])
                if d_along <= max(10.0, 4.0 * sz) and d_perp <= max(6.5, 3.5 * sz):
                    used[j] = True
                    cluster.append(cand)
                    queue.append(cand)

        avg_angle = cluster[0]["angle"]
        a_rad = math.radians(avg_angle)
        down_u = (math.sin(a_rad), -math.cos(a_rad))
        along_u = (math.cos(a_rad), math.sin(a_rad))
        cluster.sort(key=lambda t: (
            round((t["x"] * down_u[0] + t["y"] * down_u[1]), 1),
            t["x"] * along_u[0] + t["y"] * along_u[1]
        ))

        merged_lines = [t["texto"] for t in cluster if t["texto"]]
        cx = sum(t["x"] for t in cluster) / len(cluster)
        cy = sum(t["y"] for t in cluster) / len(cluster)
        blocks.append({
            "items": cluster,
            "lines": merged_lines,
            "joined_space": " ".join(merged_lines),
            "joined_nl": "\n".join(merged_lines),
            "x": cx,
            "y": cy,
            "angle": avg_angle,
            "color": cluster[0]["color"]
        })

    blocks.sort(key=lambda b: (-b["y"], b["x"]))
    return blocks


def is_sector_label(txt: str, color: str, sector_freq: Dict[str, int]) -> bool:
    up = txt.upper().strip()
    if not up:
        return False
    if RE_SECTOR_PREFIX.match(up):
        return True
    if up in KNOWN_SECTORS:
        return True
    if color == "#ff0000" and sector_freq.get(up, 0) >= 2 and not RE_ROAD_OR_WATER.search(up):
        if len(up.split()) <= 3 and not re.search(r'\d{5,}', up):
            return True
    return False


def is_non_name_cad_note(t: str) -> bool:
    """Detecta cotas sueltas (50.09 m., 69,64), rumbos (N 77°28'16" O), valores ($ 20.40 DOLARES) o cultivos/notas."""
    s = t.strip()
    if not s or RE_VERTEX_OR_NOISE.match(s) or RE_DANGLING_KEYWORD.match(s):
        return True
    if RE_MEASURE_ONLY.match(s):
        return True
    if RE_RUMBO_TEXT.match(s):
        return True
    if RE_CURRENCY_TEXT.match(s) or s.startswith("$") or "DOLARES" in s.upper():
        return True
    if RE_AREA_LINE.match(s):
        return True
    if RE_CAD_ADMIN_OR_CROP.match(s):
        return True
    return False


def classify_internal_blocks(
    inside_items: List[Dict[str, Any]],
    sector_freq: Dict[str, int]
) -> Dict[str, Any]:
    filtered = [t for t in inside_items if not RE_VERTEX_OR_NOISE.match(t["texto"])]
    if not filtered:
        return {
            "nombre_posesionario": "",
            "cedula": "",
            "nombre_predio": "",
            "sector": "",
            "area_plano": "",
            "texto_interno": ""
        }

    blocks = group_cad_text_stacks(filtered)

    cedulas: List[str] = []
    areas: List[str] = []
    sectores: List[str] = []
    nom_predios: List[str] = []
    posesionarios: List[str] = []
    all_block_texts: List[str] = []

    for blk in blocks:
        all_block_texts.append(blk["joined_nl"])
        name_parts_in_blk: List[str] = []
        pending_predio_prefix = False
        pending_sector_prefix = False
        pending_prop_prefix = False

        for item in blk["items"]:
            t = item["texto"].strip()
            up = t.upper()
            col = item.get("color", "")

            if not t or RE_VERTEX_OR_NOISE.match(t):
                continue

            if pending_predio_prefix:
                pending_predio_prefix = False
                if not RE_DANGLING_KEYWORD.match(t):
                    nom_predios.append(f"PREDIO: {t}".strip())
                continue
            if pending_sector_prefix:
                pending_sector_prefix = False
                sec_val = RE_SECTOR_PREFIX.sub("", t).strip(" .:")
                if sec_val and not RE_DANGLING_KEYWORD.match(sec_val):
                    sectores.append(sec_val)
                continue
            if pending_prop_prefix:
                pending_prop_prefix = False
                if not is_non_name_cad_note(t) and not is_sector_label(t, col, sector_freq):
                    name_parts_in_blk.append(t)
                    continue

            if up in ("PREDIO:", "PREDIO"):
                pending_predio_prefix = True
                continue
            if up in ("SECTOR:", "SECTOR", "SEC:", "SEC.", "RCTO.", "RCTO:", "RECINTO:", "COOP.", "COOP. LA", "RCTO. LAS"):
                if up in ("COOP. LA", "RCTO. LAS"):
                    sectores.append(up)
                else:
                    pending_sector_prefix = True
                continue
            if up in ("PROPIETARIO:", "PROPIETARIO", "POSESIONARIO:", "POSESIONARIO"):
                pending_prop_prefix = True
                continue

            m_prop = re.match(r'^(?:PROPIETARIO|POSESIONARIO)\s*[:.]\s*(.+)$', t, re.IGNORECASE)
            if m_prop:
                val = m_prop.group(1).strip()
                if val and not is_non_name_cad_note(val):
                    name_parts_in_blk.append(val)
                continue

            m_lote_combo = re.match(r'^((?:LOTE|SOLAR)\s*[A-Z0-9-]+)\s*[:\-]\s*(.+)$', t, re.IGNORECASE)
            if m_lote_combo:
                nom_predios.append(m_lote_combo.group(1).strip().upper())
                rest = m_lote_combo.group(2).strip()
                if rest and not is_non_name_cad_note(rest):
                    name_parts_in_blk.append(rest)
                continue

            if re.search(r'(?:C\.?\s*C\.?|C\.?\s*I\.?|CEDULA)\s*[:.]?\s*\d{9,13}', t, re.IGNORECASE) or re.fullmatch(r'\d{10}', t):
                m_ced = RE_CEDULA.search(t)
                if m_ced:
                    ced_str = m_ced.group(1)
                    if len(ced_str) == 9:
                        ced_str = "0" + ced_str
                    cedulas.append(ced_str)
                    before_cc = re.split(r'(?:C\.?\s*C\.?|C\.?\s*I\.?|CEDULA)', t, flags=re.IGNORECASE)[0].strip(" .,-:")
                    if len(before_cc) > 3 and not is_non_name_cad_note(before_cc):
                        name_parts_in_blk.append(before_cc)
                    continue

            # Área declarada en plano
            if RE_AREA_LINE.match(t) or (RE_AREA_ANY.search(t) and len(t) <= 32):
                if re.search(r'(?:MTS?2?|M2|M²|HAS?\.?|HECT)', t, re.IGNORECASE):
                    areas.append(t)
                continue

            # Sector / Recinto
            if is_sector_label(t, col, sector_freq):
                sec_clean = RE_SECTOR_PREFIX.sub("", t).strip(" .:")
                sectores.append(sec_clean or t)
                continue

            # Solar / Lote / Finca / Hacienda / Predio
            if RE_SOLAR_LOTE.match(t):
                nom_predios.append(t)
                continue

            # Notas CAD no-nombre (distancias, rumbos, cultivos, provincias, dólares)
            if is_non_name_cad_note(t) or RE_ROAD_OR_WATER.search(up):
                continue

            name_parts_in_blk.append(t)

        if name_parts_in_blk:
            joined_name = re.sub(r'\s+', ' ', " ".join(name_parts_in_blk)).strip()
            if joined_name and not RE_DANGLING_KEYWORD.match(joined_name):
                posesionarios.append(joined_name)

    sector_final = ""
    if sectores:
        merged_sec = []
        for s in sectores:
            if merged_sec and merged_sec[-1] in ("COOP. LA", "RCTO. LAS", "LA", "LAS", "EL", "LOS"):
                merged_sec[-1] = f"{merged_sec[-1]} {s}"
            elif compact_key(s) not in [compact_key(m) for m in merged_sec]:
                merged_sec.append(s)
        sector_final = " / ".join(merged_sec[:2])

    # Deduplicar posesionarios incluso frente a variantes espaciadas tipo "E L S A  A N A L U I Z A"
    uniq_pos = []
    seen_pos_keys = set()
    for p in sorted(posesionarios, key=lambda s: (len(s.split()) > 6 and s.count(" ") > len(s) * 0.35, 0)):
        ck = compact_key(p)
        if ck not in seen_pos_keys:
            seen_pos_keys.add(ck)
            uniq_pos.append(p)

    uniq_predios = []
    seen_pred_keys = set()
    for np_val in nom_predios:
        ck = compact_key(np_val)
        if ck not in seen_pred_keys:
            seen_pred_keys.add(ck)
            uniq_predios.append(np_val)

    posesionario_final = " / ".join(uniq_pos) if uniq_pos else ""
    nom_predio_final = " / ".join(uniq_predios) if uniq_predios else ""

    if not posesionario_final and nom_predio_final and not re.match(r'^(?:SOLAR|LOTE)\s+\d+', nom_predio_final, re.IGNORECASE):
        posesionario_final = nom_predio_final

    return {
        "nombre_posesionario": truncate_utf8(posesionario_final, 180),
        "cedula": cedulas[0][:20] if cedulas else "",
        "nombre_predio": truncate_utf8(nom_predio_final, 120),
        "sector": truncate_utf8(sector_final, 100),
        "area_plano": truncate_utf8(areas[0], 40) if areas else "",
        "texto_interno": "\n---\n".join(all_block_texts)
    }


def read_shapefile_from_zip(zip_path: str) -> Tuple[List[Dict[str, Any]], int]:
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        shp_n = next(n for n in names if n.lower().endswith(".shp"))
        dbf_n = next(n for n in names if n.lower().endswith(".dbf"))
        shx_n = next(n for n in names if n.lower().endswith(".shx"))

        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(shp_n)),
            dbf=io.BytesIO(z.read(dbf_n)),
            shx=io.BytesIO(z.read(shx_n)),
            encoding="latin1"
        )
        fields = [f[0] for f in reader.fields[1:]]
        shp_type = reader.shapeType
        feats = []
        for idx, sr in enumerate(reader.iterShapeRecords()):
            if sr.shape.shapeType == 0:
                continue
            props = {}
            for k, v in zip(fields, sr.record):
                props[k] = decode_smart(v) if isinstance(v, (str, bytes)) else v
            feats.append({"idx": idx, "shape": sr.shape, "props": props})
        return feats, shp_type


def main():
    t0 = time.time()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 72)
    print("CATASTRO 2026 - UNIFICACION DE POLIGONOS, TEXTOS INTERNOS Y LINDEROS")
    print("=" * 72)

    # 1. Leer textos (NOMBRES_0 + NOMBRES_01) y deduplicar
    raw_texts: List[Dict[str, Any]] = []
    seen_text_keys = set()
    for fname in ("NOMBRES_0.zip", "NOMBRES_01.zip"):
        fpath = os.path.join(INPUT_DIR, fname)
        feats, _ = read_shapefile_from_zip(fpath)
        kept = 0
        for feat in feats:
            pts = feat["shape"].points
            if not pts:
                continue
            x, y = float(pts[0][0]), float(pts[0][1])
            if not is_valid_utm_pt(x, y):
                continue
            txt = (feat["props"].get("Text") or feat["props"].get("plaintext") or "").strip()
            if not txt or txt.lower() in ("null", "none"):
                continue
            key = (round(x, 1), round(y, 1), txt.upper())
            if key in seen_text_keys:
                continue
            seen_text_keys.add(key)
            ang = normalize_cad_angle(feat["props"].get("angle", 0.0))
            col = str(feat["props"].get("color") or "#000000").strip().lower()
            try:
                sz = float(feat["props"].get("size") or 2.0)
                if not math.isfinite(sz):
                    sz = 2.0
            except Exception:
                sz = 2.0
            lng, lat = utm17s_to_wgs84(x, y)
            raw_texts.append({
                "geom": Point(x, y),
                "x": round(x, 3),
                "y": round(y, 3),
                "lng": lng,
                "lat": lat,
                "texto": txt,
                "angle": ang,
                "color": col,
                "size": round(sz, 2),
                "fuente": fname.replace(".zip", "")
            })
            kept += 1
        print(f"  [Textos] {fname}: {kept} puntos unicos validos")

    print(f"  -> Total puntos de texto unificados: {len(raw_texts)}")

    sector_freq: Dict[str, int] = {}
    for t in raw_texts:
        up = t["texto"].upper()
        sector_freq[up] = sector_freq.get(up, 0) + 1

    text_tree = STRtree([t["geom"] for t in raw_texts])

    # 2. Leer polígonos (POLIGONO_00 + POLIGONO_01)
    raw_polys: List[Dict[str, Any]] = []
    for fname in ("POLIGONO_00.zip", "POLIGONO_01.zip"):
        fpath = os.path.join(INPUT_DIR, fname)
        feats, _ = read_shapefile_from_zip(fpath)
        kept = 0
        for feat in feats:
            try:
                g = shape(feat["shape"].__geo_interface__)
            except Exception:
                continue
            for poly in extract_valid_polygons(g):
                raw_polys.append({"geom": poly, "fuente": fname.replace(".zip", "")})
                kept += 1
        print(f"  [Poligonos] {fname}: {kept} poligonos simples validos (>= 1 m2)")

    print(f"  -> Poligonos brutos totales: {len(raw_polys)}")

    # 3. Limpieza inteligente
    raw_geoms = [p["geom"] for p in raw_polys]
    raw_areas = [g.area for g in raw_geoms]
    poly_tree = STRtree(raw_geoms)

    has_sig_text = []
    for g in raw_geoms:
        gb = g.buffer(0.25)
        found = False
        for ti in text_tree.query(gb):
            t_obj = raw_texts[ti]
            if gb.contains(t_obj["geom"]) and not RE_VERTEX_OR_NOISE.match(t_obj["texto"]):
                found = True
                break
        has_sig_text.append(found)

    drop_reasons = {}
    for i in range(len(raw_polys)):
        if raw_areas[i] < 20.0 and not has_sig_text[i]:
            drop_reasons[i] = "micro_sin_texto"

    for i in range(len(raw_polys)):
        if i in drop_reasons:
            continue
        gi = raw_geoms[i]
        ai = raw_areas[i]
        for j in poly_tree.query(gi):
            if j <= i or j in drop_reasons:
                continue
            gj = raw_geoms[j]
            aj = raw_areas[j]
            inter = gi.intersection(gj).area
            if inter <= 0:
                continue
            if (inter / min(ai, aj)) >= 0.88 and (abs(ai - aj) / max(ai, aj)) <= 0.08:
                if has_sig_text[j] and not has_sig_text[i]:
                    drop_reasons[i] = "duplicado"
                    break
                else:
                    drop_reasons[j] = "duplicado"

    for i in range(len(raw_polys)):
        if i in drop_reasons:
            continue
        gi = raw_geoms[i]
        ai = raw_areas[i]
        children_areas = []
        for j in poly_tree.query(gi):
            if i == j or j in drop_reasons:
                continue
            gj = raw_geoms[j]
            aj = raw_areas[j]
            inter = gi.intersection(gj).area
            if inter <= 0:
                continue
            if aj > ai * 4.0 and ai < 120.0 and (inter / ai) >= 0.90 and not has_sig_text[i]:
                drop_reasons[i] = "construccion_interna_sin_texto"
                break
            if aj < ai * 0.98 and (inter / aj) >= 0.88 and aj >= 20.0:
                children_areas.append(aj)
        if i not in drop_reasons and len(children_areas) >= 2 and (sum(children_areas) / ai) >= 0.85:
            drop_reasons[i] = "envolvente_matriz_redundante"

    clean_polys = []
    for i, p in enumerate(raw_polys):
        if i in drop_reasons:
            continue
        norm_poly, ring_cw = normalize_ring_cw_nw(p["geom"])
        if len(ring_cw) < 3 or norm_poly.area < 1.0:
            continue
        clean_polys.append({
            "ref_id": f"URD-{len(clean_polys) + 1:05d}",
            "fuente": p["fuente"],
            "geom": norm_poly,
            "ring": ring_cw,
            "area_m2": round(norm_poly.area, 2),
            "area_ha": round(norm_poly.area / 10000.0, 4)
        })

    reasons_count = {}
    for r_val in drop_reasons.values():
        reasons_count[r_val] = reasons_count.get(r_val, 0) + 1
    print(f"  -> Limpieza de poligonos: {reasons_count}")
    print(f"  -> Poligonos limpios finales: {len(clean_polys)}")

    clean_geoms = [p["geom"] for p in clean_polys]
    clean_tree = STRtree(clean_geoms)

    text_owner_poly_idx: List[Optional[int]] = [None] * len(raw_texts)
    for ti, t_obj in enumerate(raw_texts):
        pt = t_obj["geom"]
        best_idx = None
        best_area = float("inf")
        for pi in clean_tree.query(pt.buffer(0.25)):
            if clean_geoms[pi].buffer(0.20).contains(pt):
                if clean_geoms[pi].area < best_area:
                    best_area = clean_geoms[pi].area
                    best_idx = pi
        text_owner_poly_idx[ti] = best_idx

    # 4. Asignar textos INTERNOS
    poly_inside_texts: List[List[Dict[str, Any]]] = [[] for _ in range(len(clean_polys))]
    for ti, pi in enumerate(text_owner_poly_idx):
        if pi is not None:
            poly_inside_texts[pi].append(raw_texts[ti])

    for pi, p in enumerate(clean_polys):
        inside = poly_inside_texts[pi]
        parsed = classify_internal_blocks(inside, sector_freq)
        p["nombre"] = parsed["nombre_posesionario"]
        p["cedula"] = parsed["cedula"]
        p["nombre_predio"] = parsed["nombre_predio"]
        p["sector"] = parsed["sector"]
        p["area_plano"] = parsed["area_plano"]
        p["texto_interno"] = parsed["texto_interno"]
        p["textos_internos"] = [
            {
                "texto": t["texto"],
                "x": t["x"],
                "y": t["y"],
                "lng": t["lng"],
                "lat": t["lat"],
                "angle": t["angle"],
                "color": t["color"],
                "size": t["size"]
            }
            for t in inside
            if not RE_VERTEX_OR_NOISE.match(t["texto"])
        ]

    # 5. Pre-agrupar bloques exteriores libres LIMPIOS (ya filtrando cotas/sectores/rumbos antes de agrupar)
    free_external_items = [
        raw_texts[ti]
        for ti, pi in enumerate(text_owner_poly_idx)
        if pi is None
        and not is_non_name_cad_note(raw_texts[ti]["texto"])
        and not is_sector_label(raw_texts[ti]["texto"], raw_texts[ti]["color"], sector_freq)
        and not RE_SOLAR_LOTE.match(raw_texts[ti]["texto"])
    ]
    ext_blocks = group_cad_text_stacks(free_external_items)
    ext_block_pts = [Point(b["x"], b["y"]) for b in ext_blocks]
    ext_block_tree = STRtree(ext_block_pts)

    valid_texts_idx = [
        ti for ti, t in enumerate(raw_texts)
        if not is_non_name_cad_note(t["texto"])
        and not is_sector_label(t["texto"], t["color"], sector_freq)
    ]
    valid_text_tree = STRtree([raw_texts[ti]["geom"] for ti in valid_texts_idx])

    def get_neighbor_label(pj: int) -> str:
        np = clean_polys[pj]
        if np["nombre"] and np["nombre_predio"]:
            if compact_key(np["nombre_predio"]) in compact_key(np["nombre"]):
                return np["nombre"]
            return f"{np['nombre']} ({np['nombre_predio']})"
        return np["nombre"] or np["nombre_predio"] or f"PREDIO {np['ref_id']}"

    # 6. Topología, Linderos y Colindantes
    metadata_completa: Dict[str, Dict[str, Any]] = {}
    all_lindero_lines: List[Dict[str, Any]] = []
    report_rows: List[List[Any]] = []

    con_nombre = 0
    con_sector = 0
    con_txt_interno = 0
    total_linderos = 0
    linderos_con_colindante = 0

    for pi, p in enumerate(clean_polys):
        ring = p["ring"]
        n = len(ring)
        orientations = get_cardinal_orientations(ring)
        linderos_list: List[Dict[str, Any]] = []
        col_by_dir: Dict[str, List[str]] = {"NORTE": [], "ESTE": [], "SUR": [], "OESTE": []}

        poly_buf = p["geom"].buffer(2.0)
        cand_neighbors = [j for j in clean_tree.query(poly_buf) if j != pi]

        for ei in range(n):
            p1 = ring[ei]
            p2 = ring[(ei + 1) % n]
            v1_cod = f"P{ei + 1:02d}"
            v2_cod = f"P{((ei + 1) % n) + 1:02d}"
            tramo = f"{v1_cod} - {v2_cod}"
            rumbo, longitud = calcular_rumbo_utm(p1, p2)
            orientacion = orientations[ei] if ei < len(orientations) else "NORTE"

            seg_line = LineString([p1, p2])
            seg_len = max(seg_line.length, 1e-6)
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            out_nx = -dy / seg_len
            out_ny = dx / seg_len

            colindante = ""

            # Paso A: Etiqueta exterior libre cercana
            seg_ext_buf = seg_line.buffer(24.0)
            best_ext_txt = ""
            best_ext_score = float("inf")
            for bi in ext_block_tree.query(seg_ext_buf):
                blk = ext_blocks[bi]
                pt = ext_block_pts[bi]
                u = ((pt.x - p1[0]) * dx + (pt.y - p1[1]) * dy) / (seg_len * seg_len)
                if not (-0.25 <= u <= 1.25):
                    continue
                proj_x = p1[0] + u * dx
                proj_y = p1[1] + u * dy
                d_perp = math.hypot(pt.x - proj_x, pt.y - proj_y)
                if d_perp > 28.0:
                    continue
                side_dot = (pt.x - proj_x) * out_nx + (pt.y - proj_y) * out_ny
                if side_dot < -1.5:
                    continue
                txt_cand = blk["joined_space"].strip()
                edge_pen = 0.0 if (0.0 <= u <= 1.0) else min(abs(u), abs(u - 1.0)) * seg_len * 0.8
                score = d_perp + edge_pen
                if score < best_ext_score:
                    best_ext_score = score
                    best_ext_txt = txt_cand

            # Paso B: Verificar polígono vecino usando segmento recortado al 15%-85% para NO enganchar vértices esquineros
            core_seg = substring(seg_line, 0.15 * seg_len, 0.85 * seg_len) if seg_len > 3.0 else seg_line
            core_len = max(core_seg.length, 0.5)
            seg_buf = core_seg.buffer(0.95)
            best_neighbors: List[Tuple[float, str, float]] = []
            for j in cand_neighbors:
                gj = clean_geoms[j]
                if not seg_buf.intersects(gj):
                    continue
                inter_len = seg_buf.intersection(gj.boundary).length
                if inter_len <= 0:
                    inter_len = seg_buf.intersection(gj).area / 0.95
                if inter_len >= min(1.2, core_len * 0.25):
                    lbl = get_neighbor_label(j)
                    cent_j = gj.centroid
                    u_n = ((cent_j.x - p1[0]) * dx + (cent_j.y - p1[1]) * dy) / (seg_len * seg_len)
                    best_neighbors.append((u_n, lbl, inter_len))

            if best_neighbors:
                best_neighbors.sort(key=lambda x: -x[2])
                if best_ext_txt and RE_ROAD_OR_WATER.search(best_ext_txt) and best_ext_score < 16.0:
                    colindante = best_ext_txt
                else:
                    named_neighbors = [bn for bn in best_neighbors if not bn[1].startswith("PREDIO URD-")]
                    if named_neighbors:
                        uniq_n = []
                        for _, lbl, _ in sorted(named_neighbors, key=lambda x: x[0]):
                            if lbl not in uniq_n:
                                uniq_n.append(lbl)
                        colindante = " / ".join(uniq_n[:2])
                    elif best_ext_txt and best_ext_score <= 22.0:
                        colindante = best_ext_txt
                    else:
                        colindante = best_neighbors[0][1]
            elif best_ext_txt:
                colindante = best_ext_txt
            else:
                best_fb = ""
                best_fb_d = 35.0
                for v_pos in valid_text_tree.query(seg_line.buffer(35.0)):
                    ti = valid_texts_idx[v_pos]
                    if text_owner_poly_idx[ti] == pi:
                        continue
                    t_obj = raw_texts[ti]
                    pt = t_obj["geom"]
                    u = ((pt.x - p1[0]) * dx + (pt.y - p1[1]) * dy) / (seg_len * seg_len)
                    if not (-0.15 <= u <= 1.15):
                        continue
                    proj_x = p1[0] + u * dx
                    proj_y = p1[1] + u * dy
                    side_dot = (pt.x - proj_x) * out_nx + (pt.y - proj_y) * out_ny
                    if side_dot <= 0.0:
                        continue
                    d_perp = math.hypot(pt.x - proj_x, pt.y - proj_y)
                    if d_perp < best_fb_d:
                        best_fb_d = d_perp
                        best_fb = t_obj["texto"]
                colindante = best_fb

            colindante = truncate_utf8(colindante, 250)
            if colindante:
                linderos_con_colindante += 1
                if colindante not in col_by_dir[orientacion]:
                    col_by_dir[orientacion].append(colindante)
            total_linderos += 1

            linderos_list.append({
                "tramo": tramo,
                "orientacion": orientacion,
                "longitud": longitud,
                "rumbo": rumbo,
                "colindante": colindante
            })

            all_lindero_lines.append({
                "coords": [p1, p2],
                "ref_id": p["ref_id"],
                "tramo": tramo,
                "orientacion": orientacion,
                "longitud": longitud,
                "rumbo": rumbo,
                "colindante": colindante,
                "nombre": p["nombre"],
                "nombre_predio": p["nombre_predio"]
            })

        p["linderos"] = linderos_list
        p["col_norte"] = truncate_utf8(", ".join(col_by_dir["NORTE"]), 254)
        p["col_este"] = truncate_utf8(", ".join(col_by_dir["ESTE"]), 254)
        p["col_sur"] = truncate_utf8(", ".join(col_by_dir["SUR"]), 254)
        p["col_oeste"] = truncate_utf8(", ".join(col_by_dir["OESTE"]), 254)

        if p["nombre"]:
            con_nombre += 1
        if p["sector"]:
            con_sector += 1
        if p["texto_interno"]:
            con_txt_interno += 1

        metadata_completa[p["ref_id"]] = {
            "ref_id": p["ref_id"],
            "fuente": p["fuente"],
            "nombre_posesionario": p["nombre"],
            "cedula": p["cedula"],
            "nombre_predio": p["nombre_predio"],
            "sector": p["sector"],
            "area_plano": p["area_plano"],
            "area_ha": p["area_ha"],
            "area_m2": p["area_m2"],
            "texto_interno": p["texto_interno"],
            "textos_internos": p["textos_internos"],
            "linderos": linderos_list
        }

        report_rows.append([
            p["ref_id"], p["fuente"], p["nombre"], p["cedula"], p["nombre_predio"],
            p["sector"], p["area_ha"], p["area_m2"], p["area_plano"],
            p["texto_interno"].replace("\n", " | "),
            len(linderos_list), p["col_norte"], p["col_este"], p["col_sur"], p["col_oeste"]
        ])

    # 7. Escribir archivos de salida (.zip)
    predios_base = os.path.join(OUTPUT_DIR, "PREDIOS_URDANETA_UNIFICADO")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w_p = shapefile.Writer(predios_base, shapeType=shapefile.POLYGON, encoding="utf-8")
        w_p.field("REF_ID", "C", 20)
        w_p.field("FUENTE", "C", 20)
        w_p.field("NOMBRE", "C", 180)
        w_p.field("CEDULA", "C", 20)
        w_p.field("NOM_PREDIO", "C", 120)
        w_p.field("SECTOR", "C", 100)
        w_p.field("AREA_HA", "N", 14, 4)
        w_p.field("AREA_M2", "N", 14, 2)
        w_p.field("AREA_PLANO", "C", 40)
        w_p.field("TXT_INTERN", "C", 254)
        w_p.field("LIND_NORTE", "C", 254)
        w_p.field("LIND_ESTE", "C", 254)
        w_p.field("LIND_SUR", "C", 254)
        w_p.field("LIND_OESTE", "C", 254)
        w_p.field("NUM_LIN", "N", 6, 0)

        for p in clean_polys:
            ext_ring = p["ring"] + [p["ring"][0]]
            parts = [ext_ring]
            for interior in p["geom"].interiors:
                int_pts = [(round(float(x), 3), round(float(y), 3)) for x, y, *_ in interior.coords]
                if len(int_pts) >= 4:
                    parts.append(int_pts)
            w_p.poly(parts)
            w_p.record(
                p["ref_id"],
                p["fuente"],
                truncate_utf8(p["nombre"], 180),
                truncate_utf8(p["cedula"], 20),
                truncate_utf8(p["nombre_predio"], 120),
                truncate_utf8(p["sector"], 100),
                p["area_ha"],
                p["area_m2"],
                truncate_utf8(p["area_plano"], 40),
                truncate_utf8(p["texto_interno"].replace("\n", " | "), 254),
                p["col_norte"],
                p["col_este"],
                p["col_sur"],
                p["col_oeste"],
                len(p["linderos"])
            )
        w_p.close()

    with open(predios_base + ".prj", "w", encoding="utf-8") as f:
        f.write(PRJ_EPSG_32717)
    with open(predios_base + ".cpg", "w", encoding="utf-8") as f:
        f.write("UTF-8")

    meta_json_path = os.path.join(OUTPUT_DIR, "predios_metadata_completa.json")
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(metadata_completa, f, ensure_ascii=False)

    predios_zip_path = predios_base + ".zip"
    with zipfile.ZipFile(predios_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            zf.write(predios_base + ext, arcname="PREDIOS_URDANETA_UNIFICADO" + ext)
        zf.write(meta_json_path, arcname="predios_metadata_completa.cmeta")

    lind_base = os.path.join(OUTPUT_DIR, "LINDEROS_URDANETA_UNIFICADO")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w_l = shapefile.Writer(lind_base, shapeType=shapefile.POLYLINE, encoding="utf-8")
        w_l.field("REF_ID", "C", 20)
        w_l.field("TRAMO", "C", 20)
        w_l.field("ORIENTAC", "C", 15)
        w_l.field("LONGITUD", "N", 12, 2)
        w_l.field("RUMBO", "C", 40)
        w_l.field("COLINDANTE", "C", 254)
        w_l.field("NOMBRE", "C", 180)
        w_l.field("NOM_PREDIO", "C", 120)
        for ln in all_lindero_lines:
            w_l.line([ln["coords"]])
            w_l.record(
                ln["ref_id"],
                ln["tramo"],
                ln["orientacion"],
                ln["longitud"],
                truncate_utf8(ln["rumbo"], 40),
                truncate_utf8(ln["colindante"], 254),
                truncate_utf8(ln["nombre"], 180),
                truncate_utf8(ln["nombre_predio"], 120)
            )
        w_l.close()
    with open(lind_base + ".prj", "w", encoding="utf-8") as f:
        f.write(PRJ_EPSG_32717)
    with open(lind_base + ".cpg", "w", encoding="utf-8") as f:
        f.write("UTF-8")
    with zipfile.ZipFile(lind_base + ".zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            zf.write(lind_base + ext, arcname="LINDEROS_URDANETA_UNIFICADO" + ext)

    nom_base = os.path.join(OUTPUT_DIR, "NOMBRES_URDANETA_UNIFICADO")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        w_n = shapefile.Writer(nom_base, shapeType=shapefile.POINT, encoding="utf-8")
        w_n.field("texto", "C", 254)
        w_n.field("txtangle", "N", 10, 2)
        w_n.field("color", "C", 20)
        w_n.field("size", "N", 8, 2)
        w_n.field("fuente", "C", 20)
        for t in raw_texts:
            w_n.point(t["x"], t["y"])
            w_n.record(truncate_utf8(t["texto"], 254), t["angle"], t["color"][:20], t["size"], t["fuente"][:20])
        w_n.close()
    with open(nom_base + ".prj", "w", encoding="utf-8") as f:
        f.write(PRJ_EPSG_32717)
    with open(nom_base + ".cpg", "w", encoding="utf-8") as f:
        f.write("UTF-8")
    with zipfile.ZipFile(nom_base + ".zip", "w", zipfile.ZIP_DEFLATED) as zf:
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            zf.write(nom_base + ext, arcname="NOMBRES_URDANETA_UNIFICADO" + ext)

    csv_path = os.path.join(OUTPUT_DIR, "REPORTE_UNIFICACION.csv")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        cw = csv.writer(f)
        cw.writerow([
            "REF_ID", "FUENTE", "POSESIONARIO", "CEDULA", "NOM_PREDIO", "SECTOR",
            "AREA_HA", "AREA_M2", "AREA_PLANO", "TXT_INTERNO",
            "NUM_LINDEROS", "LIND_NORTE", "LIND_ESTE", "LIND_SUR", "LIND_OESTE"
        ])
        cw.writerows(report_rows)

    print("-" * 72)
    print(f"Tiempo total: {time.time() - t0:.2f} s")
    print(f"Predios unificados: {len(clean_polys)}")
    print(f"  Con texto interno guardado   : {con_txt_interno} ({con_txt_interno * 100 / max(1, len(clean_polys)):.1f}%)")
    print(f"  Con posesionario identificado: {con_nombre} ({con_nombre * 100 / max(1, len(clean_polys)):.1f}%)")
    print(f"  Con sector identificado      : {con_sector} ({con_sector * 100 / max(1, len(clean_polys)):.1f}%)")
    print(f"Linderos generados: {total_linderos} | Con colindante asignado: {linderos_con_colindante} ({linderos_con_colindante * 100 / max(1, total_linderos):.1f}%)")
    print(f"Archivos generados en: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
