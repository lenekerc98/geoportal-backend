import os
import math
import logging
import json
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy import text
from app.core.database import engine

logger = logging.getLogger("catastro")


def utm17s_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """
    Conversión matemática de alta precisión (sub-milimétrica)
    de UTM Zona 17 Sur (EPSG:32717) a WGS84 Geográficas (EPSG:4326 - Lon, Lat).
    """
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e = math.sqrt(1 - (b / a) ** 2)
    e_prime_sq = (e * a / b) ** 2
    k0 = 0.9996

    # Zona 17S: Meridiano central = -81 grados
    lon_origin = -81.0
    x = easting - 500000.0
    y = northing - 10000000.0  # Hemisferio sur

    m = y / k0
    mu = m / (a * (1 - e**2 / 4 - 3 * e**4 / 64 - 5 * e**6 / 256))
    e1 = (1 - math.sqrt(1 - e**2)) / (1 + math.sqrt(1 - e**2))

    phi1_rad = (
        mu
        + (3 * e1 / 2 - 27 * e1**3 / 32) * math.sin(2 * mu)
        + (21 * e1**2 / 16 - 55 * e1**4 / 32) * math.sin(4 * mu)
        + (151 * e1**3 / 96) * math.sin(6 * mu)
    )

    n1 = a / math.sqrt(1 - e**2 * math.sin(phi1_rad) ** 2)
    t1 = math.tan(phi1_rad) ** 2
    c1 = e_prime_sq * math.cos(phi1_rad) ** 2
    r1 = a * (1 - e**2) / (1 - e**2 * math.sin(phi1_rad) ** 2) ** 1.5
    d = x / (n1 * k0)

    lat = phi1_rad - (n1 * math.tan(phi1_rad) / r1) * (
        d**2 / 2
        - (5 + 3 * t1 + 10 * c1 - 4 * c1**2 - 9 * e_prime_sq) * d**4 / 24
        + (61 + 90 * t1 + 298 * c1 + 45 * t1**2 - 252 * e_prime_sq - 3 * c1**2) * d**6 / 720
    )
    lon = (
        d
        - (1 + 2 * t1 + c1) * d**3 / 6
        + (5 - 2 * c1 + 28 * t1 - 3 * c1**2 + 8 * e_prime_sq + 24 * t1**2) * d**5 / 120
    ) / math.cos(phi1_rad)

    lat_deg = math.degrees(lat)
    lon_deg = lon_origin + math.degrees(lon)
    return lon_deg, lat_deg


def get_sqlserver_connection():
    """
    Obtiene una conexión de SOLO LECTURA a la base SQL Server municipal.
    Importa pyodbc de forma diferida para no romper endpoints solo-PostgreSQL en Render/Docker.
    """
    try:
        import pyodbc
    except ImportError as exc:
        logger.error("[SQLServer] El módulo 'pyodbc' no está instalado en este entorno.")
        raise RuntimeError(
            "La sincronización directa con SQL Server requiere 'pyodbc' y el driver ODBC."
        ) from exc

    host = os.getenv("SQLSERVER_HOST", "192.168.18.22")
    port = os.getenv("SQLSERVER_PORT", "1433")
    database = os.getenv("SQLSERVER_DB", "muvp_urdaneta")
    user = os.getenv("SQLSERVER_USER", "sa")
    password = os.getenv("SQLSERVER_PASSWORD", "vent@n@s2016")
    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host},{port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
        f"ApplicationIntent=ReadOnly;"
        f"Connection Timeout=5;"
    )

    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        return conn
    except Exception as e:
        logger.error(f"[SQLServer] Error conectando a {host}/{database}: {e}")
        if "ODBC Driver 18" in driver:
            try:
                fallback_conn_str = conn_str.replace("ODBC Driver 18", "ODBC Driver 17")
                return pyodbc.connect(fallback_conn_str, timeout=5)
            except Exception as e2:
                logger.error(f"[SQLServer Fallback Driver 17] Falló también: {e2}")
        raise e


def sync_sqlserver_to_postgres() -> int:
    """
    Lee los puntos de SQL Server municipal y los sincroniza/actualiza
    en el esquema 'interoperabilidad.referencias_prediales' de PostgreSQL.
    """
    conn_sql = get_sqlserver_connection()
    cursor = conn_sql.cursor()

    query = """
        SELECT 
            s.CodCatastral,
            s.IDTitular,
            LTRIM(RTRIM(ISNULL(t.Apellidos, '') + ' ' + ISNULL(t.Nombres, ''))) AS Propietario,
            s.NombrePredio,
            s.SITIO,
            s.RCX,
            s.RCY,
            s.RCFAREA,
            s.RCOTRO
        FROM RurSolar s WITH (NOLOCK)
        LEFT JOIN TitularesPredio t WITH (NOLOCK) ON (
            s.IDTitular = t.Identificacion OR 
            s.IDTitular = CAST(t.IdTitular AS VARCHAR(50))
        )
        WHERE s.RCX > 100000 AND s.RCY > 1000000
        ORDER BY s.CodCatastral
    """
    cursor.execute(query)
    rows = cursor.fetchall()

    insert_query = text("""
        INSERT INTO interoperabilidad.referencias_prediales (
            cod_catastral, id_titular, propietario, nombre_predio, sitio,
            rcx, rcy, area_ref, geom, geom_4326, fecha_sincronizacion
        )
        VALUES (
            :cod_catastral, :id_titular, :propietario, :nombre_predio, :sitio,
            :rcx, :rcy, :area_ref,
            ST_SetSRID(ST_Point(:rcx, :rcy), 32717),
            ST_SetSRID(ST_Point(:lon, :lat), 4326),
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (cod_catastral, rcx, rcy) DO UPDATE SET
            id_titular = EXCLUDED.id_titular,
            propietario = EXCLUDED.propietario,
            nombre_predio = EXCLUDED.nombre_predio,
            sitio = EXCLUDED.sitio,
            area_ref = EXCLUDED.area_ref,
            geom = EXCLUDED.geom,
            geom_4326 = EXCLUDED.geom_4326,
            fecha_sincronizacion = CURRENT_TIMESTAMP;
    """)

    count = 0
    with engine.begin() as pg_conn:
        for r in rows:
            cod_catastral = str(r[0] or "").strip()
            id_titular = str(r[1] or "").strip()
            propietario = str(r[2] or "").strip()
            nombre_predio = str(r[3] or "").strip()
            sitio = str(r[4] or "").strip()
            rcx = float(r[5]) if r[5] is not None else None
            rcy = float(r[6]) if r[6] is not None else None
            rcf_area = str(r[7] or "").strip()

            if rcx is None or rcy is None:
                continue

            try:
                lon, lat = utm17s_to_wgs84(rcx, rcy)
                if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                    continue
            except Exception:
                continue

            pg_conn.execute(insert_query, {
                "cod_catastral": cod_catastral,
                "id_titular": id_titular,
                "propietario": propietario,
                "nombre_predio": nombre_predio,
                "sitio": sitio,
                "rcx": rcx,
                "rcy": rcy,
                "area_ref": rcf_area,
                "lon": lon,
                "lat": lat
            })
            count += 1

    cursor.close()
    conn_sql.close()
    return count


def get_referencias_prediales(force_sync: bool = False) -> Dict[str, Any]:
    """
    Obtiene los Puntos de Referencia Predial desde el esquema PostgreSQL 'interoperabilidad.referencias_prediales'.
    Si la tabla está vacía o si se solicita 'force_sync', sincroniza primero desde SQL Server.
    """
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM interoperabilidad.referencias_prediales")).scalar() or 0

    if total == 0 or force_sync:
        try:
            sync_sqlserver_to_postgres()
        except Exception as e:
            logger.error(f"Error sincronizando SQL Server a PostgreSQL: {e}")
            if total == 0:
                raise e

    query = text("""
        SELECT 
            cod_catastral,
            id_titular,
            propietario,
            nombre_predio,
            sitio,
            rcx,
            rcy,
            area_ref,
            ST_AsGeoJSON(geom_4326) AS geojson
        FROM interoperabilidad.referencias_prediales
        WHERE activo = TRUE
        ORDER BY cod_catastral;
    """)

    features = []
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
        for r in rows:
            geom = json.loads(r.geojson) if r.geojson else None
            if not geom:
                continue

            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "cod_catastral": r.cod_catastral,
                    "id_titular": r.id_titular,
                    "propietario": r.propietario,
                    "nombre_predio": r.nombre_predio,
                    "sitio": r.sitio,
                    "rcx": float(r.rcx) if r.rcx is not None else None,
                    "rcy": float(r.rcy) if r.rcy is not None else None,
                    "area_ref": r.area_ref,
                    "origen": "PostgreSQL_interoperabilidad"
                }
            })

    return {
        "type": "FeatureCollection",
        "total": len(features),
        "source": "PostgreSQL: interoperabilidad.referencias_prediales",
        "features": features
    }


def find_referencia_en_poligono(geom_geojson: Dict[str, Any], srid: int = 32717) -> Optional[Dict[str, Any]]:
    """
    Dado un polígono GeoJSON (el predio que el usuario dibujó),
    hace un spatial join con PostGIS para encontrar qué Punto de Referencia
    de SQL Server se encuentra dentro del polígono.
    Incluye información territorial para detectar discrepancias (Opción 2).
    """
    geom_str = json.dumps(geom_geojson)
    query = text(f"""
        SELECT 
            r.cod_catastral,
            r.id_titular,
            r.propietario,
            r.nombre_predio,
            r.sitio,
            r.rcx,
            r.rcy,
            r.area_ref,
            c.codigo_dpa as cod_parroquia_territorial,
            UPPER(c.nombre) as nombre_parroquia_territorial
        FROM interoperabilidad.referencias_prediales r
        LEFT JOIN catastro.ciudades c ON c.codigo_dpa LIKE '1206%' AND ST_Intersects(r.geom, c.geom)
        WHERE ST_Contains(
            ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), {srid}), 32717),
            r.geom
        )
        ORDER BY ST_Distance(
            ST_Centroid(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(:geom_json), {srid}), 32717)),
            r.geom
        ) ASC
        LIMIT 1;
    """)

    with engine.connect() as conn:
        row = conn.execute(query, {"geom_json": geom_str}).fetchone()
        if row:
            cod_sql = str(row.cod_catastral or '').strip()
            parr_sql = cod_sql[4:6] if len(cod_sql) >= 6 else None
            cod_dpa_terr = str(row.cod_parroquia_territorial or '')
            parr_terr_num = cod_dpa_terr[-2:] if len(cod_dpa_terr) >= 2 else None
            
            return {
                "cod_catastral": row.cod_catastral,
                "id_titular": row.id_titular,
                "propietario": row.propietario,
                "nombre_predio": row.nombre_predio,
                "sitio": row.sitio,
                "rcx": float(row.rcx) if row.rcx is not None else None,
                "rcy": float(row.rcy) if row.rcy is not None else None,
                "area_ref": row.area_ref,
                "parroquia_sql": parr_sql,
                "parroquia_territorial_cod": parr_terr_num,
                "parroquia_territorial_nombre": row.nombre_parroquia_territorial,
                "tiene_discrepancia_parroquia": bool(parr_sql and parr_terr_num and parr_sql != parr_terr_num)
            }
    return None
