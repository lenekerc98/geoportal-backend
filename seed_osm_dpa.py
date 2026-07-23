import os
import requests
import json
import time
from sqlalchemy import text
from app.core.database import SessionLocal

def get_nominatim_polygon(query):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "polygon_geojson": 1,
        "limit": 1
    }
    headers = {
        "User-Agent": "GeoportalCatastroEcuador/1.0 (test@example.com)"
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            if "geojson" in data[0]:
                return data[0]["geojson"]
    return None

def update_dpa_geometries():
    db = SessionLocal()
    try:
        # Update Provincias
        provincias = db.execute(text("SELECT id, nombre FROM catastro.provincias WHERE geom IS NULL")).fetchall()
        for p in provincias:
            print(f"Obteniendo límites para provincia: {p.nombre}")
            geom = get_nominatim_polygon(f"Provincia de {p.nombre}, Ecuador")
            if not geom:
                geom = get_nominatim_polygon(f"{p.nombre}, Ecuador")
            
            if geom and geom["type"] in ["Polygon", "MultiPolygon"]:
                if geom["type"] == "Polygon":
                    geom["type"] = "MultiPolygon"
                    geom["coordinates"] = [geom["coordinates"]]
                
                geojson_str = json.dumps(geom)
                db.execute(text("UPDATE catastro.provincias SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326) WHERE id = :id"), {"geojson": geojson_str, "id": p.id})
                db.commit()
                print(f"Límites de {p.nombre} actualizados.")
            else:
                print(f"No se encontró polígono para {p.nombre}.")
            time.sleep(1) # Polite delay
                
        # Update Cantones
        cantones = db.execute(text("SELECT c.id, c.nombre, p.nombre as prov_nombre FROM catastro.cantones c JOIN catastro.provincias p ON c.id_provincia = p.id WHERE c.geom IS NULL")).fetchall()
        for c in cantones:
            print(f"Obteniendo límites para cantón: {c.nombre}, {c.prov_nombre}")
            geom = get_nominatim_polygon(f"Cantón {c.nombre}, {c.prov_nombre}, Ecuador")
            if not geom:
                geom = get_nominatim_polygon(f"{c.nombre}, {c.prov_nombre}, Ecuador")
                
            if geom and geom["type"] in ["Polygon", "MultiPolygon"]:
                if geom["type"] == "Polygon":
                    geom["type"] = "MultiPolygon"
                    geom["coordinates"] = [geom["coordinates"]]
                
                geojson_str = json.dumps(geom)
                db.execute(text("UPDATE catastro.cantones SET geom = ST_SetSRID(ST_GeomFromGeoJSON(:geojson), 4326) WHERE id = :id"), {"geojson": geojson_str, "id": c.id})
                db.commit()
                print(f"Límites de {c.nombre} actualizados.")
            else:
                print(f"No se encontró polígono para cantón {c.nombre}.")
            time.sleep(1) # Polite delay
                
        print("Proceso completado.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_dpa_geometries()
