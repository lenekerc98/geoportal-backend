import os
from sqlalchemy import text
from app.core.database import SessionLocal

def run_seed():
    db = SessionLocal()
    try:
        print("Recreando tablas DPA...")
        
        # Eliminar las restricciones de otras tablas (ortofotos_catalogo)
        db.execute(text("""
            ALTER TABLE IF EXISTS catastro.ortofotos_catalogo 
            DROP CONSTRAINT IF EXISTS ortofotos_catalogo_id_provincia_fkey,
            DROP CONSTRAINT IF EXISTS ortofotos_catalogo_id_canton_fkey,
            DROP CONSTRAINT IF EXISTS ortofotos_catalogo_id_ciudad_fkey;
        """))
        
        db.execute(text("""
            DROP TABLE IF EXISTS catastro.ciudades CASCADE;
            DROP TABLE IF EXISTS catastro.cantones CASCADE;
            DROP TABLE IF EXISTS catastro.provincias CASCADE;
        """))
        
        # Crear tabla provincias
        db.execute(text("""
            CREATE TABLE catastro.provincias (
                id SERIAL PRIMARY KEY,
                codigo_dpa VARCHAR(2) UNIQUE NOT NULL,
                nombre VARCHAR(100) NOT NULL UNIQUE
            )
        """))
        
        # Crear tabla cantones
        db.execute(text("""
            CREATE TABLE catastro.cantones (
                id SERIAL PRIMARY KEY,
                codigo_dpa VARCHAR(4) UNIQUE NOT NULL,
                id_provincia INTEGER REFERENCES catastro.provincias(id) ON DELETE CASCADE,
                nombre VARCHAR(100) NOT NULL
            )
        """))
        
        # Crear tabla ciudades/parroquias
        db.execute(text("""
            CREATE TABLE catastro.ciudades (
                id SERIAL PRIMARY KEY,
                codigo_dpa VARCHAR(6) UNIQUE NOT NULL,
                id_canton INTEGER REFERENCES catastro.cantones(id) ON DELETE CASCADE,
                nombre VARCHAR(100) NOT NULL
            )
        """))
        
        # Restaurar foreign keys en ortofotos_catalogo
        try:
            db.execute(text("""
                ALTER TABLE catastro.ortofotos_catalogo
                ADD CONSTRAINT ortofotos_catalogo_id_provincia_fkey FOREIGN KEY (id_provincia) REFERENCES catastro.provincias(id) ON DELETE SET NULL,
                ADD CONSTRAINT ortofotos_catalogo_id_canton_fkey FOREIGN KEY (id_canton) REFERENCES catastro.cantones(id) ON DELETE SET NULL,
                ADD CONSTRAINT ortofotos_catalogo_id_ciudad_fkey FOREIGN KEY (id_ciudad) REFERENCES catastro.ciudades(id) ON DELETE SET NULL;
            """))
        except Exception as e:
            print("Nota: No se pudieron restaurar las foreign keys de ortofotos_catalogo, puede que la tabla no exista aún.")
            db.execute(text("ROLLBACK TO SAVEPOINT before_fkeys;"))
        
        db.commit()
        
        print("Insertando Provincias y Cantones principales con DPA oficial...")
        
        import json
        with open(os.path.join(os.path.dirname(__file__), 'data', 'dpa_ecuador.json'), 'r', encoding='utf-8') as f:
            dpa_data = json.load(f)
        
        for prov in dpa_data:
            # Insertar Provincia
            db.execute(text("INSERT INTO catastro.provincias (codigo_dpa, nombre) VALUES (:cod, :n)"), {"cod": prov["codigo"], "n": prov["nombre"].title()})
            prov_id = db.execute(text("SELECT id FROM catastro.provincias WHERE codigo_dpa=:cod"), {"cod": prov["codigo"]}).scalar()
            
            # Insertar Cantones
            for can in prov.get("cantones", []):
                db.execute(text("INSERT INTO catastro.cantones (codigo_dpa, id_provincia, nombre) VALUES (:cod, :id_prov, :n)"), 
                           {"cod": can["codigo"], "id_prov": prov_id, "n": can["nombre"].title()})
                can_id = db.execute(text("SELECT id FROM catastro.cantones WHERE codigo_dpa=:cod"), {"cod": can["codigo"]}).scalar()
                
                # Insertar Parroquias
                parroquias = can.get("parroquias", [])
                for par in parroquias:
                    db.execute(text("INSERT INTO catastro.ciudades (codigo_dpa, id_canton, nombre) VALUES (:cod, :id_can, :n)"), 
                               {"cod": par["codigo"], "id_can": can_id, "n": par["nombre"].title()})

        db.commit()
        print("Base de datos DPA migrada y configurada con códigos reales con éxito.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
