from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal, engine
from sqlalchemy import text
from app.models.user import Empresa

def migrate():
    db = SessionLocal()
    try:
        # 1. Update Empresa parameters
        e = db.query(Empresa).first()
        if e:
            # Recreate dictionary to trigger SQLAlchemy JSON modification tracking
            params = dict(e.parametros) if e.parametros else {}
            params["defaultCenter"] = [-1.5833, -79.4667]
            params["defaultZoom"] = 14
            e.parametros = params
            db.add(e)
            print(f"Updated parameters for Empresa: {e.nombre}")

        # 2. Create catastro.elementos_adicionales table
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS catastro.elementos_adicionales (
                id SERIAL PRIMARY KEY,
                capa_id INTEGER REFERENCES catastro.capas_adicionales(id) ON DELETE CASCADE,
                geom GEOMETRY,
                propiedades JSONB
            );
        """))
        print("Created table catastro.elementos_adicionales")

        # 3. Find and drop all shape_ tables in catastro schema
        result = db.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'catastro' AND tablename LIKE 'shape_%'
        """))
        tables_to_drop = [row[0] for row in result]
        
        for table in tables_to_drop:
            db.execute(text(f"DROP TABLE catastro.{table} CASCADE"))
            print(f"Dropped table catastro.{table}")

        # Also clear capas_adicionales to start fresh as agreed with user
        db.execute(text("DELETE FROM catastro.capas_adicionales CASCADE"))
        print("Cleared catastro.capas_adicionales")

        db.commit()
        print("Migration successful")
    except Exception as ex:
        db.rollback()
        print(f"Migration failed: {ex}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
