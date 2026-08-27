import os
import re
import json
import math
import logging
from typing import Dict, Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from psycopg2.extras import execute_values

try:
    import ezdxf
    EZDXF_AVAILABLE = True
except ImportError:
    EZDXF_AVAILABLE = False


def _sanitize_coord(val: float) -> str:
    """Evita -0.0000 y formatea a 4 decimales limpios"""
    if abs(val) < 1e-7:
        val = 0.0
    return f"{val:.4f}"


def _parse_dxf_native(file_path: str) -> List[Dict[str, Any]]:
    """
    Parser nativo de archivos DXF ASCII en Python puro.
    Interpreta todas las lineas, polilineas, circulos y arcos como LINESTRING (Polilineas)
    y los textos/puntos como POINT.
    """
    lines = []
    for encoding in ('utf-8', 'latin-1', 'cp1252', 'iso-8859-1'):
        try:
            with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                lines = [line.strip() for line in f]
            break
        except Exception:
            continue

    if not lines:
        raise ValueError("El archivo DXF esta vacio o no se pudo leer.")

    # Convertir a pares (group_code, value)
    pairs: List[Tuple[int, str]] = []
    i = 0
    while i < len(lines) - 1:
        code_str = lines[i]
        val = lines[i + 1]
        try:
            code = int(code_str)
            pairs.append((code, val))
            i += 2
        except ValueError:
            i += 1

    in_entities = False
    entities_data = []
    
    current_entity = None
    polyline_vertices = []
    is_in_polyline = False

    idx = 0
    while idx < len(pairs):
        code, val = pairs[idx]

        if code == 0 and val.upper() == 'SECTION':
            if idx + 1 < len(pairs) and pairs[idx + 1][0] == 2 and pairs[idx + 1][1].upper() == 'ENTITIES':
                in_entities = True
                idx += 2
                continue

        if in_entities and code == 0 and val.upper() == 'ENDSEC':
            in_entities = False
            break

        if not in_entities:
            if code == 0 and val.upper() in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'TEXT', 'MTEXT', 'POINT', 'CIRCLE', 'ARC', 'HATCH'):
                in_entities = True

        if in_entities:
            if code == 0:
                if current_entity:
                    if is_in_polyline and val.upper() == 'VERTEX':
                        pass
                    elif is_in_polyline and val.upper() == 'SEQEND':
                        current_entity['vertices'] = polyline_vertices
                        entities_data.append(current_entity)
                        current_entity = None
                        is_in_polyline = False
                        polyline_vertices = []
                    else:
                        if is_in_polyline:
                            current_entity['vertices'] = polyline_vertices
                            is_in_polyline = False
                            polyline_vertices = []
                        entities_data.append(current_entity)
                        current_entity = None

                etype = val.upper()
                if etype == 'VERTEX' and is_in_polyline:
                    current_vertex = {}
                    idx += 1
                    while idx < len(pairs) and pairs[idx][0] != 0:
                        vcode, vval = pairs[idx]
                        if vcode == 10: current_vertex['x'] = float(vval)
                        elif vcode == 20: current_vertex['y'] = float(vval)
                        elif vcode == 30: current_vertex['z'] = float(vval)
                        idx += 1
                    if 'x' in current_vertex and 'y' in current_vertex:
                        polyline_vertices.append((current_vertex['x'], current_vertex['y']))
                    continue
                elif etype in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'TEXT', 'MTEXT', 'POINT', 'CIRCLE', 'ARC', 'HATCH'):
                    current_entity = {
                        'type': etype,
                        'layer': 'DEFAULT',
                        'color': '',
                        'points': [],
                        'text': '',
                        'flags': 0
                    }
                    if etype == 'POLYLINE':
                        is_in_polyline = True
                        polyline_vertices = []
                    else:
                        is_in_polyline = False

            elif current_entity:
                if code == 8:
                    current_entity['layer'] = str(val).strip().upper()
                elif code == 62:
                    current_entity['color'] = str(val).strip()
                elif code in (1, 3):
                    if not current_entity['text']:
                        current_entity['text'] = str(val)
                    else:
                        current_entity['text'] += " " + str(val)
                elif code == 70:
                    try: current_entity['flags'] = int(val)
                    except ValueError: pass
                else:
                    if code == 10:
                        try: current_entity['x'] = float(val)
                        except ValueError: pass
                        if current_entity['type'] == 'LWPOLYLINE':
                            current_entity['points'].append({'x': float(val)})
                    elif code == 20:
                        try: current_entity['y'] = float(val)
                        except ValueError: pass
                        if current_entity['type'] == 'LWPOLYLINE' and current_entity['points']:
                            current_entity['points'][-1]['y'] = float(val)
                    elif code == 30:
                        try: current_entity['z'] = float(val)
                        except ValueError: pass
                    elif code == 11:
                        try: current_entity['x2'] = float(val)
                        except ValueError: pass
                    elif code == 21:
                        try: current_entity['y2'] = float(val)
                        except ValueError: pass
                    elif code == 31:
                        try: current_entity['z2'] = float(val)
                        except ValueError: pass
                    elif code == 40:
                        try: current_entity['radius'] = float(val)
                        except ValueError: pass
                    elif code == 50:
                        try: current_entity['start_angle'] = float(val)
                        except ValueError: pass
                    elif code == 51:
                        try: current_entity['end_angle'] = float(val)
                        except ValueError: pass

        idx += 1

    if current_entity:
        if is_in_polyline:
            current_entity['vertices'] = polyline_vertices
        entities_data.append(current_entity)

    # Convertir todas las lineas, polilineas y circulos a LINESTRING
    elementos = []
    for ent in entities_data:
        etype = ent.get('type')
        layer = ent.get('layer', 'DEFAULT')
        color = ent.get('color', '')
        text_val = ent.get('text', '').strip()
        flags = ent.get('flags', 0)
        
        wkt = None
        tipo_geom = None

        if etype == 'LINE':
            if 'x' in ent and 'y' in ent and 'x2' in ent and 'y2' in ent:
                x1, y1 = _sanitize_coord(ent['x']), _sanitize_coord(ent['y'])
                x2, y2 = _sanitize_coord(ent['x2']), _sanitize_coord(ent['y2'])
                wkt = f"LINESTRING({x1} {y1}, {x2} {y2})"
                tipo_geom = "LineString"

        elif etype == 'LWPOLYLINE':
            pts = [f"{_sanitize_coord(p['x'])} {_sanitize_coord(p['y'])}" for p in ent.get('points', []) if 'x' in p and 'y' in p]
            if len(pts) >= 2:
                is_closed = (flags & 1) == 1
                if is_closed and pts[0] != pts[-1]:
                    pts.append(pts[0])
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

        elif etype == 'POLYLINE':
            pts = [f"{_sanitize_coord(v[0])} {_sanitize_coord(v[1])}" for v in ent.get('vertices', [])]
            if len(pts) >= 2:
                is_closed = (flags & 1) == 1
                if is_closed and pts[0] != pts[-1]:
                    pts.append(pts[0])
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

        elif etype in ('TEXT', 'MTEXT'):
            if 'x' in ent and 'y' in ent:
                wkt = f"POINT({_sanitize_coord(ent['x'])} {_sanitize_coord(ent['y'])})"
                tipo_geom = "Point"
                if text_val:
                    text_val = re.sub(r'\\[A-Za-z0-9]+;', '', text_val)
                    text_val = text_val.replace('\\P', ' ').replace('{', '').replace('}', '').strip()

        elif etype == 'POINT':
            if 'x' in ent and 'y' in ent:
                wkt = f"POINT({_sanitize_coord(ent['x'])} {_sanitize_coord(ent['y'])})"
                tipo_geom = "Point"

        elif etype == 'CIRCLE':
            if 'x' in ent and 'y' in ent and 'radius' in ent:
                cx, cy, rad = ent['x'], ent['y'], ent['radius']
                angles = [i * (2 * math.pi / 24) for i in range(24)]
                pts = [f"{_sanitize_coord(cx + rad * math.cos(a))} {_sanitize_coord(cy + rad * math.sin(a))}" for a in angles]
                pts.append(pts[0])
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

        elif etype == 'ARC':
            if 'x' in ent and 'y' in ent and 'radius' in ent:
                cx, cy, rad = ent['x'], ent['y'], ent['radius']
                sa = math.radians(ent.get('start_angle', 0))
                ea = math.radians(ent.get('end_angle', 360))
                if ea < sa: ea += 2 * math.pi
                steps = 16
                ss = (ea - sa) / steps
                angles = [sa + i * ss for i in range(steps + 1)]
                pts = [f"{_sanitize_coord(cx + rad * math.cos(a))} {_sanitize_coord(cy + rad * math.sin(a))}" for a in angles]
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

        if wkt and tipo_geom:
            elementos.append({
                "capa_cad": layer,
                "tipo_geometria": tipo_geom,
                "texto": text_val or None,
                "color": color or None,
                "wkt": wkt,
                "propiedades": json.dumps({"dxftype": etype, "layer": layer, "color": color, "text": text_val or ""})
            })

    return elementos


def _parse_dxf_ezdxf(file_path: str) -> List[Dict[str, Any]]:
    """
    Parser ultrarrapido usando la libreria ezdxf que interpreta todas las geometrias vectoriales como LINESTRING.
    """
    doc = ezdxf.readfile(file_path)
    msp = doc.modelspace()
    elementos = []

    for entity in msp:
        layer_name = str(getattr(entity.dxf, 'layer', 'DEFAULT') or "DEFAULT").strip().upper()
        dxftype = entity.dxftype()
        color_code = str(getattr(entity.dxf, 'color', ''))
        wkt = None
        tipo_geom = None
        texto_val = None

        try:
            if dxftype == 'LINE':
                start, end = entity.dxf.start, entity.dxf.end
                x1, y1 = _sanitize_coord(start.x), _sanitize_coord(start.y)
                x2, y2 = _sanitize_coord(end.x), _sanitize_coord(end.y)
                wkt = f"LINESTRING({x1} {y1}, {x2} {y2})"
                tipo_geom = "LineString"

            elif dxftype == 'LWPOLYLINE':
                points = list(entity.get_points())
                if len(points) >= 2:
                    pts = [f"{_sanitize_coord(p[0])} {_sanitize_coord(p[1])}" for p in points]
                    if entity.is_closed and pts[0] != pts[-1]:
                        pts.append(pts[0])
                    wkt = f"LINESTRING({', '.join(pts)})"
                    tipo_geom = "LineString"

            elif dxftype == 'POLYLINE':
                points = [v.dxf.location for v in entity.vertices]
                if len(points) >= 2:
                    pts = [f"{_sanitize_coord(p.x)} {_sanitize_coord(p.y)}" for p in points]
                    if entity.is_closed and pts[0] != pts[-1]:
                        pts.append(pts[0])
                    wkt = f"LINESTRING({', '.join(pts)})"
                    tipo_geom = "LineString"

            elif dxftype in ('TEXT', 'MTEXT'):
                insert = entity.dxf.insert
                wkt = f"POINT({_sanitize_coord(insert.x)} {_sanitize_coord(insert.y)})"
                tipo_geom = "Point"
                if dxftype == 'TEXT':
                    texto_val = entity.dxf.text
                else:
                    texto_val = entity.text
                if texto_val:
                    texto_val = re.sub(r'\\[A-Za-z0-9]+;', '', texto_val)
                    texto_val = texto_val.replace('\\P', ' ').replace('{', '').replace('}', '').strip()

            elif dxftype == 'POINT':
                loc = entity.dxf.location
                wkt = f"POINT({_sanitize_coord(loc.x)} {_sanitize_coord(loc.y)})"
                tipo_geom = "Point"

            elif dxftype == 'CIRCLE':
                center, radius = entity.dxf.center, entity.dxf.radius
                angles = [i * (2 * math.pi / 24) for i in range(24)]
                pts = [f"{_sanitize_coord(center.x + radius * math.cos(a))} {_sanitize_coord(center.y + radius * math.sin(a))}" for a in angles]
                pts.append(pts[0])
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

            elif dxftype == 'ARC':
                center, radius = entity.dxf.center, entity.dxf.radius
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                steps = 16
                step_size = (end_angle - start_angle) / steps
                angles = [start_angle + i * step_size for i in range(steps + 1)]
                pts = [f"{_sanitize_coord(center.x + radius * math.cos(a))} {_sanitize_coord(center.y + radius * math.sin(a))}" for a in angles]
                wkt = f"LINESTRING({', '.join(pts)})"
                tipo_geom = "LineString"

            if wkt and tipo_geom:
                elementos.append({
                    "capa_cad": layer_name,
                    "tipo_geometria": tipo_geom,
                    "texto": texto_val,
                    "color": color_code,
                    "wkt": wkt,
                    "propiedades": json.dumps({"dxftype": dxftype, "layer": layer_name, "color": color_code, "text": texto_val or ""})
                })
        except Exception as ent_err:
            logging.debug(f"Saltando entidad {dxftype}: {ent_err}")
            continue

    return elementos


def procesar_archivo_dxf(
    file_path: str,
    nombre_archivo: str,
    db: Session,
    srid: int = 32717,
    empresa_id: int = None
) -> Dict[str, Any]:
    """
    Procesa un archivo DXF de AutoCAD interpretando las entidades lineales y poligonales
    como LINESTRING (Polilineas) y las almacena de forma ultrarrapida en catastro.capas_cad_cartas
    y sincroniza su catalogo en catastro.cartas_topograficas.
    """
    elementos = []
    
    # 1. Intentar con ezdxf (altamente optimizado)
    if EZDXF_AVAILABLE:
        try:
            elementos = _parse_dxf_ezdxf(file_path)
        except Exception as ez_err:
            logging.warning(f"ezdxf fallo ({ez_err}), recurriendo al parser nativo.")
            elementos = []

    # 2. Si ezdxf no encontro entidades, usar el parser nativo
    if not elementos:
        elementos = _parse_dxf_native(file_path)

    if not elementos:
        raise ValueError("No se encontraron entidades vectoriales compatibles en el archivo DXF.")

    capas_detectadas = sorted(list(set(e["capa_cad"] for e in elementos)))

    # 3. Eliminar registros anteriores del mismo archivo
    db.execute(text("DELETE FROM catastro.capas_cad_cartas WHERE nombre_archivo = :archivo"), {"archivo": nombre_archivo})
    db.commit()

    # 4. Insercion masiva ultrarrapida usando psycopg2 execute_values
    data_tuples = [
        (
            nombre_archivo,
            e["capa_cad"],
            e["tipo_geometria"],
            e.get("texto"),
            e.get("color"),
            e["wkt"],
            e["propiedades"]
        )
        for e in elementos
    ]

    insert_query = f"""
        INSERT INTO catastro.capas_cad_cartas 
            (nombre_archivo, formato_origen, capa_cad, tipo_geometria, texto, color, geom, propiedades)
        VALUES %s
    """
    template = f"(%s, 'CAD', %s, %s, %s, %s, ST_GeomFromText(%s, {srid}), %s::jsonb)"

    raw_conn = db.connection().connection
    cursor = raw_conn.cursor()
    execute_values(cursor, insert_query, data_tuples, template=template, page_size=5000)
    db.commit()

    # 5. Registrar o sincronizar en catastro.cartas_topograficas con nombre limpio
    try:
        base_name = os.path.splitext(nombre_archivo)[0]
        cod_match = re.search(r'([A-Za-z0-9]+-[A-Za-z0-9]+)', base_name)
        default_cod = cod_match.group(1).upper() if cod_match else "NIV-D3"
        
        clean_name = re.sub(r'^[A-Za-z0-9]+-[A-Za-z0-9]+', '', base_name).replace('-', ' ').replace('_', ' ').strip().upper()
        if not clean_name:
            clean_name = base_name.upper()
            
        final_codigo = (codigo or default_cod).strip().upper()
        final_nombre = (nombre or clean_name).strip().upper()
        final_cuadricula = (cuadricula or default_cod).strip().upper()
        final_escala = (escala or "1:50000").strip()

        db.execute(text("""
            INSERT INTO catastro.cartas_topograficas (nombre_archivo, codigo, nombre, cuadricula, escala, fecha_creacion)
            VALUES (:nombre_archivo, :codigo, :nombre, :cuadricula, :escala, NOW())
            ON CONFLICT (nombre_archivo) DO UPDATE
            SET codigo = EXCLUDED.codigo,
                nombre = EXCLUDED.nombre,
                cuadricula = EXCLUDED.cuadricula,
                escala = EXCLUDED.escala;
        """), {
            "nombre_archivo": nombre_archivo,
            "codigo": final_codigo,
            "nombre": final_nombre,
            "cuadricula": final_cuadricula,
            "escala": final_escala
        })
        db.commit()
    except Exception as meta_err:
        logging.warning(f"No se pudo sincronizar catalogo de cartas_topograficas: {meta_err}")

    return {
        "nombre_archivo": nombre_archivo,
        "formato_origen": "CAD",
        "total_entidades": len(elementos),
        "capas_detectadas": capas_detectadas
    }
