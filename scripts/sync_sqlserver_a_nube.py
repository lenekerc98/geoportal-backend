"""
Script de Sincronización Push: SQL Server Local ➔ PostgreSQL en AWS RDS
======================================================================
Este script lee los datos alfanuméricos y referencias de la base de datos
municipal de SQL Server en tu laptop (muvp_urdaneta_) y los sube directamente
a la base de datos de PostgreSQL en la nube (AWS RDS).

Sincroniza:
1. Referencias espaciales (interoperabilidad.referencias_prediales)
2. Posesionarios y Cédulas (catastro.posesionario)
3. Catálogo de Códigos Catastrales de 19 dígitos (catastro.codigo_catastral)
4. Enlace automático con los predios existentes en la nube (catastro.predio)
"""

import os
import sys
import math
import pyodbc
import psycopg2
from typing import Tuple
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Cargar variables de entorno
env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(env_path)

DB_URL_PG = os.getenv("DATABASE_URL")
if not DB_URL_PG:
    print("[ERROR] DATABASE_URL no encontrada en backend/.env")
    sys.exit(1)


def utm17s_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """Conversión matemática de UTM 17S a WGS84 Geográficas (Lon, Lat)."""
    a = 6378137.0
    f = 1 / 298.257223563
    b = a * (1 - f)
    e = math.sqrt(1 - (b / a) ** 2)
    e_prime_sq = (e * a / b) ** 2
    k0 = 0.9996
    lon_origin = -81.0

    x = easting - 500000.0
    y = northing - 10000000.0

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

    return math.degrees(lon) + lon_origin, math.degrees(lat)


def get_sqlserver_conn():
    """Intenta conectar a SQL Server local por Windows Auth o por sa en la red."""
    # 1. Intentar local con Windows Auth
    candidates = [
        r"DRIVER={ODBC Driver 18 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=muvp_urdaneta_;Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=3;",
        r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\SQLEXPRESS;DATABASE=muvp_urdaneta_;Trusted_Connection=yes;TrustServerCertificate=yes;Connection Timeout=3;",
        r"DRIVER={SQL Server};SERVER=.\SQLEXPRESS;DATABASE=muvp_urdaneta_;Trusted_Connection=yes;Connection Timeout=3;",
    ]

    host = os.getenv("SQLSERVER_HOST", "192.168.18.22")
    port = os.getenv("SQLSERVER_PORT", "1433")
    db = os.getenv("SQLSERVER_DB", "muvp_urdaneta")
    user = os.getenv("SQLSERVER_USER", "sa")
    pwd = os.getenv("SQLSERVER_PASSWORD", "vent@n@s2016")

    candidates.append(
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={host},{port};DATABASE={db};UID={user};PWD={pwd};TrustServerCertificate=yes;Connection Timeout=3;"
    )

    for c in candidates:
        try:
            conn = pyodbc.connect(c, timeout=3)
            return conn
        except Exception:
            continue

    raise Exception("No se pudo conectar a SQL Server (probado en .\\SQLEXPRESS y 192.168.18.22)")


def main():
    print("=" * 70)
    print("🚀 INICIANDO SINCRONIZACIÓN: SQL SERVER LOCAL ➔ POSTGRESQL AWS RDS")
    print("=" * 70)

    # 1. Conectar a SQL Server
    print("\n[1/4] Conectando a SQL Server municipal...")
    try:
        conn_sql = get_sqlserver_conn()
        print("  ✓ Conectado exitosamente a SQL Server municipal.")
    except Exception as e:
        print(f"  ❌ Error conectando a SQL Server: {e}")
        sys.exit(1)

    # 2. Conectar a PostgreSQL en AWS RDS
    print("\n[2/4] Conectando a PostgreSQL en AWS RDS...")
    try:
        conn_pg = psycopg2.connect(DB_URL_PG)
        cur_pg = conn_pg.cursor()
        print("  ✓ Conectado exitosamente a AWS RDS.")
    except Exception as e:
        print(f"  ❌ Error conectando a PostgreSQL AWS RDS: {e}")
        conn_sql.close()
        sys.exit(1)

    # 3. Extraer predios y titulares de SQL Server
    print("\n[3/4] Leyendo predios rurales y titulares de SQL Server...")
    cur_sql = conn_sql.cursor()
    query_sql = """
        SELECT 
            LTRIM(RTRIM(s.CodCatastral)) AS CodCatastral,
            LTRIM(RTRIM(ISNULL(s.IDTitular, ''))) AS IDTitular,
            LTRIM(RTRIM(ISNULL(t.Apellidos, '') + ' ' + ISNULL(t.Nombres, ''))) AS Propietario,
            LTRIM(RTRIM(ISNULL(s.NombrePredio, ''))) AS NombrePredio,
            LTRIM(RTRIM(ISNULL(s.SITIO, ''))) AS Sector,
            s.RCX,
            s.RCY,
            s.RCFAREA
        FROM RurSolar s WITH (NOLOCK)
        LEFT JOIN TitularesPredio t WITH (NOLOCK) ON (
            s.IDTitular = t.Identificacion OR 
            s.IDTitular = CAST(t.IdTitular AS VARCHAR(50))
        )
        ORDER BY s.CodCatastral;
    """
    cur_sql.execute(query_sql)
    rows = cur_sql.fetchall()
    total_sql = len(rows)
    print(f"  ✓ {total_sql:,} registros obtenidos de SQL Server.")

    # 4. Sincronizar hacia AWS RDS
    print("\n[4/4] Sincronizando datos hacia PostgreSQL en AWS RDS...")

    # Crear esquema y tabla si no existieran
    cur_pg.execute("""
        CREATE SCHEMA IF NOT EXISTS interoperabilidad;
        CREATE TABLE IF NOT EXISTS interoperabilidad.referencias_prediales (
            id SERIAL PRIMARY KEY,
            cod_catastral VARCHAR(50),
            id_titular VARCHAR(50),
            propietario VARCHAR(255),
            nombre_predio VARCHAR(255),
            sitio VARCHAR(150),
            rcx NUMERIC,
            rcy NUMERIC,
            area_ref VARCHAR(50),
            geom geometry(Point, 32717),
            geom_4326 geometry(Point, 4326),
            fecha_sincronizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT uq_ref_predial UNIQUE (cod_catastral, rcx, rcy)
        );
        CREATE INDEX IF NOT EXISTS idx_ref_geom ON interoperabilidad.referencias_prediales USING GIST (geom);
        CREATE INDEX IF NOT EXISTS idx_ref_cod ON interoperabilidad.referencias_prediales (cod_catastral);
    """)
    conn_pg.commit()

    count_posesionarios = 0
    count_codigos = 0
    count_referencias = 0
    count_predios_enlazados = 0

    # Cache en memoria de posesionarios en Postgres para no duplicar consultas
    cur_pg.execute("SELECT cedula, id FROM catastro.posesionario WHERE cedula IS NOT NULL AND cedula != '';")
    pos_cache = {r[0].strip(): r[1] for r in cur_pg.fetchall()}

    for idx, r in enumerate(rows, 1):
        cod = str(r[0] or "").strip()
        ced = str(r[1] or "").strip()
        nom = str(r[2] or "").strip()
        nom_predio = str(r[3] or "").strip()
        sector = str(r[4] or "").strip()
        rcx = float(r[5]) if r[5] is not None else None
        rcy = float(r[6]) if r[6] is not None else None
        area_str = str(r[7] or "").strip()

        if not cod:
            continue

        # A. Sincronizar Posesionario si tiene cédula y nombre
        pos_id = None
        if ced and len(ced) >= 8:
            if ced in pos_cache:
                pos_id = pos_cache[ced]
            else:
                cur_pg.execute(
                    "INSERT INTO catastro.posesionario (cedula, nombre, empresa_id) VALUES (%s, %s, 2) RETURNING id;",
                    (ced, nom or "TITULAR REGISTRADO")
                )
                pos_id = cur_pg.fetchone()[0]
                pos_cache[ced] = pos_id
                count_posesionarios += 1

        # B. Registrar Código Catastral en el catálogo
        cur_pg.execute("""
            INSERT INTO catastro.codigo_catastral (codigo, posesionario_id, empresa_id, activo)
            VALUES (%s, %s, 2, TRUE)
            ON CONFLICT (codigo) DO UPDATE SET
                posesionario_id = COALESCE(catastro.codigo_catastral.posesionario_id, EXCLUDED.posesionario_id);
        """, (cod, pos_id))
        count_codigos += 1

        # C. Referencia Espacial
        if rcx and rcy and rcx > 100000 and rcy > 1000000:
            try:
                lon, lat = utm17s_to_wgs84(rcx, rcy)
                if -180 <= lon <= 180 and -90 <= lat <= 90:
                    cur_pg.execute("""
                        INSERT INTO interoperabilidad.referencias_prediales (
                            cod_catastral, id_titular, propietario, nombre_predio, sitio,
                            rcx, rcy, area_ref, geom, geom_4326, fecha_sincronizacion
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s,
                            ST_SetSRID(ST_Point(%s, %s), 32717),
                            ST_SetSRID(ST_Point(%s, %s), 4326),
                            CURRENT_TIMESTAMP
                        )
                        ON CONFLICT (cod_catastral, rcx, rcy) DO UPDATE SET
                            id_titular = EXCLUDED.id_titular,
                            propietario = EXCLUDED.propietario,
                            nombre_predio = EXCLUDED.nombre_predio,
                            sitio = EXCLUDED.sitio,
                            fecha_sincronizacion = CURRENT_TIMESTAMP;
                    """, (cod, ced, nom, nom_predio, sector, rcx, rcy, area_str, rcx, rcy, lon, lat))
                    count_referencias += 1
            except Exception:
                pass

        # D. Enlace automático con predios existentes en catastro.predio
        if pos_id or sector:
            cur_pg.execute("""
                UPDATE catastro.predio
                SET posesionario_id = COALESCE(posesionario_id, %s),
                    sector = COALESCE(NULLIF(sector, ''), %s)
                WHERE cod_catastral = %s AND (posesionario_id IS NULL OR sector IS NULL OR sector = '');
            """, (pos_id, sector or None, cod))
            if cur_pg.rowcount > 0:
                count_predios_enlazados += cur_pg.rowcount

        if idx % 1000 == 0 or idx == total_sql:
            conn_pg.commit()
            print(f"  ... Procesados {idx:,} / {total_sql:,} registros ({idx * 100 // total_sql}%)")

    conn_pg.commit()
    cur_sql.close()
    conn_sql.close()
    cur_pg.close()
    conn_pg.close()

    print("\n" + "=" * 70)
    print("🎉 SINCRONIZACIÓN COMPLETADA CON ÉXITO")
    print("=" * 70)
    print(f"  • Posesionarios nuevos creados en la nube:   {count_posesionarios:,}")
    print(f"  • Códigos catastrales asegurados en catálogo: {count_codigos:,}")
    print(f"  • Referencias espaciales cargadas (puntos):  {count_referencias:,}")
    print(f"  • Predios poligonales enlazados con titular: {count_predios_enlazados:,}")
    print("=" * 70)


if __name__ == "__main__":
    main()
