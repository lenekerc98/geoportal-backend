import json
import os
from sqlalchemy import text
from app.core.database import SessionLocal

def seed_full_dpa():
    db = SessionLocal()
    try:
        print("Cargando JSON de DPA...")
        json_path = r"C:\Users\leneker\.gemini\antigravity-ide\brain\bb73e56e-8e4c-4e3f-8a68-8c7bb9eff4b3\.system_generated\steps\3582\content.md"
        
        with open(json_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Extract json part (skip frontmatter)
        json_str = ""
        in_json = False
        for line in lines:
            if line.strip() == "[" or line.strip() == "{":
                in_json = True
            if in_json:
                json_str += line
                
        data = json.loads(json_str)
        
        print("Iniciando inserción de datos DPA...")
        for prov in data:
            prov_name = prov.get("Province")
            if not prov_name: continue
            
            # 1. Insertar Provincia
            q_prov = text("SELECT id FROM catastro.provincias WHERE nombre ILIKE :nombre")
            res_prov = db.execute(q_prov, {"nombre": prov_name}).fetchone()
            
            if res_prov:
                prov_id = res_prov[0]
            else:
                res = db.execute(text("INSERT INTO catastro.provincias (nombre) VALUES (:nombre) RETURNING id"), {"nombre": prov_name})
                prov_id = res.fetchone()[0]
                
            # 2. Insertar Cantones
            cantones = prov.get("cantons", [])
            for cant in cantones:
                cant_name = cant.get("Canton")
                cap_name = cant.get("Capital")
                
                if not cant_name: continue
                
                q_cant = text("SELECT id FROM catastro.cantones WHERE nombre ILIKE :nombre AND id_provincia = :prov_id")
                res_cant = db.execute(q_cant, {"nombre": cant_name, "prov_id": prov_id}).fetchone()
                
                if res_cant:
                    cant_id = res_cant[0]
                else:
                    res = db.execute(text("INSERT INTO catastro.cantones (id_provincia, nombre) VALUES (:prov, :nombre) RETURNING id"), 
                                   {"prov": prov_id, "nombre": cant_name})
                    cant_id = res.fetchone()[0]
                    
                # 3. Insertar Ciudades / Capitales
                if cap_name:
                    q_cap = text("SELECT id FROM catastro.ciudades WHERE nombre ILIKE :nombre AND id_canton = :cant_id")
                    res_cap = db.execute(q_cap, {"nombre": cap_name, "cant_id": cant_id}).fetchone()
                    
                    if not res_cap:
                        db.execute(text("INSERT INTO catastro.ciudades (id_canton, nombre) VALUES (:cant, :nombre)"), 
                                 {"cant": cant_id, "nombre": cap_name})
                        
        db.commit()
        print("¡Base de datos DPA poblada exitosamente con todos los cantones y ciudades!")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_full_dpa()
