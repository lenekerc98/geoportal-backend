import os
from sqlalchemy import text
from app.core.database import SessionLocal

def run_seed():
    db = SessionLocal()
    try:
        print("Creando tablas DPA...")
        # Crear tabla provincias
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS catastro.provincias (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE
            )
        """))
        
        # Crear tabla cantones
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS catastro.cantones (
                id SERIAL PRIMARY KEY,
                id_provincia INTEGER REFERENCES catastro.provincias(id) ON DELETE CASCADE,
                nombre VARCHAR(100) NOT NULL
            )
        """))
        
        # Crear tabla ciudades/parroquias
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS catastro.ciudades (
                id SERIAL PRIMARY KEY,
                id_canton INTEGER REFERENCES catastro.cantones(id) ON DELETE CASCADE,
                nombre VARCHAR(100) NOT NULL
            )
        """))
        
        # Modificar ortofotos_catalogo
        db.execute(text("""
            ALTER TABLE catastro.ortofotos_catalogo
            ADD COLUMN IF NOT EXISTS id_provincia INTEGER REFERENCES catastro.provincias(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS id_canton INTEGER REFERENCES catastro.cantones(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS id_ciudad INTEGER REFERENCES catastro.ciudades(id) ON DELETE SET NULL
        """))
        
        db.commit()
        
        print("Insertando Provincias...")
        provincias_ec = [
            'Azuay', 'Bolívar', 'Cañar', 'Carchi', 'Chimborazo', 'Cotopaxi', 'El Oro', 'Esmeraldas',
            'Galápagos', 'Guayas', 'Imbabura', 'Loja', 'Los Ríos', 'Manabí', 'Morona Santiago',
            'Napo', 'Orellana', 'Pastaza', 'Pichincha', 'Santa Elena', 'Santo Domingo de los Tsáchilas',
            'Sucumbíos', 'Tungurahua', 'Zamora Chinchipe'
        ]
        
        for p in provincias_ec:
            db.execute(text("INSERT INTO catastro.provincias (nombre) VALUES (:n) ON CONFLICT (nombre) DO NOTHING"), {"n": p})
            
        db.commit()
        
        # Insertar algunos cantones y ciudades de ejemplo para Pichincha y Guayas
        print("Insertando Cantones y Ciudades de ejemplo...")
        
        # Pichincha
        pichincha_id = db.execute(text("SELECT id FROM catastro.provincias WHERE nombre='Pichincha'")).scalar()
        if pichincha_id:
            db.execute(text("INSERT INTO catastro.cantones (id_provincia, nombre) SELECT :id, 'Quito' WHERE NOT EXISTS (SELECT 1 FROM catastro.cantones WHERE nombre='Quito' AND id_provincia=:id)"), {"id": pichincha_id})
            quito_id = db.execute(text("SELECT id FROM catastro.cantones WHERE nombre='Quito'")).scalar()
            if quito_id:
                for ciudad in ['Calderón', 'Chillogallo', 'Centro Histórico']:
                    db.execute(text("INSERT INTO catastro.ciudades (id_canton, nombre) SELECT :id, :n WHERE NOT EXISTS (SELECT 1 FROM catastro.ciudades WHERE nombre=:n AND id_canton=:id)"), {"id": quito_id, "n": ciudad})
                    
        # Guayas
        guayas_id = db.execute(text("SELECT id FROM catastro.provincias WHERE nombre='Guayas'")).scalar()
        if guayas_id:
            db.execute(text("INSERT INTO catastro.cantones (id_provincia, nombre) SELECT :id, 'Guayaquil' WHERE NOT EXISTS (SELECT 1 FROM catastro.cantones WHERE nombre='Guayaquil' AND id_provincia=:id)"), {"id": guayas_id})
            gye_id = db.execute(text("SELECT id FROM catastro.cantones WHERE nombre='Guayaquil'")).scalar()
            if gye_id:
                for ciudad in ['Tarqui', 'Ximena', 'Rocafuerte']:
                    db.execute(text("INSERT INTO catastro.ciudades (id_canton, nombre) SELECT :id, :n WHERE NOT EXISTS (SELECT 1 FROM catastro.ciudades WHERE nombre=:n AND id_canton=:id)"), {"id": gye_id, "n": ciudad})

        # Los Ríos (por el usuario)
        rios_id = db.execute(text("SELECT id FROM catastro.provincias WHERE nombre='Los Ríos'")).scalar()
        if rios_id:
            db.execute(text("INSERT INTO catastro.cantones (id_provincia, nombre) SELECT :id, 'Babahoyo' WHERE NOT EXISTS (SELECT 1 FROM catastro.cantones WHERE nombre='Babahoyo' AND id_provincia=:id)"), {"id": rios_id})
            baba_id = db.execute(text("SELECT id FROM catastro.cantones WHERE nombre='Babahoyo'")).scalar()
            if baba_id:
                for ciudad in ['Clemente Baquerizo', 'Barreiro']:
                    db.execute(text("INSERT INTO catastro.ciudades (id_canton, nombre) SELECT :id, :n WHERE NOT EXISTS (SELECT 1 FROM catastro.ciudades WHERE nombre=:n AND id_canton=:id)"), {"id": baba_id, "n": ciudad})

        db.commit()
        print("Base de datos DPA configurada con éxito.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
