import os
from sqlalchemy import text
from app.core.database import SessionLocal

def migrate():
    db = SessionLocal()
    try:
        print("Iniciando migracion de Proyectos y Parametros de Empresas...")
        
        # 1. Alter Empresa (Report parameters)
        db.execute(text("""
            ALTER TABLE catastro.empresa 
            ADD COLUMN IF NOT EXISTS logo_url VARCHAR(500),
            ADD COLUMN IF NOT EXISTS nombre_alcalde VARCHAR(200),
            ADD COLUMN IF NOT EXISTS nombre_director VARCHAR(200),
            ADD COLUMN IF NOT EXISTS sbu_actual NUMERIC(10,2),
            ADD COLUMN IF NOT EXISTS valor_m2_urbano NUMERIC(10,2),
            ADD COLUMN IF NOT EXISTS valor_m2_rural NUMERIC(10,2);
        """))
        
        # Remove backwards relation from empresa if it exists
        try:
            db.execute(text("ALTER TABLE catastro.empresa DROP COLUMN proyecto_id;"))
        except:
            db.rollback() # It might not exist, that's fine
            
        # 2. Alter Proyecto (or create it if it didn't really exist properly)
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS catastro.proyecto (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                descripcion TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # Add Empresa FK and Map Parameters to Proyecto
        db.execute(text("""
            ALTER TABLE catastro.proyecto
            ADD COLUMN IF NOT EXISTS empresa_id INTEGER REFERENCES catastro.empresa(id) ON DELETE CASCADE,
            ADD COLUMN IF NOT EXISTS estado VARCHAR(50) DEFAULT 'Activo',
            ADD COLUMN IF NOT EXISTS map_lat NUMERIC(15,8) DEFAULT -1.5833,
            ADD COLUMN IF NOT EXISTS map_lng NUMERIC(15,8) DEFAULT -79.4667,
            ADD COLUMN IF NOT EXISTS map_zoom INTEGER DEFAULT 14,
            ADD COLUMN IF NOT EXISTS map_basemap VARCHAR(100) DEFAULT 'osm';
        """))
        
        # 3. Alter Predio
        db.execute(text("""
            ALTER TABLE catastro.predio
            ADD COLUMN IF NOT EXISTS proyecto_id INTEGER REFERENCES catastro.proyecto(id) ON DELETE SET NULL;
        """))
        
        db.commit()
        print("Migracion completada con exito.")
    except Exception as e:
        db.rollback()
        print(f"Error en la migracion: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
