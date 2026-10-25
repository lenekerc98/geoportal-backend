import os
from sqlalchemy import text
from app.core.database import SessionLocal

def migrate_dpa():
    db = SessionLocal()
    try:
        print("Agregando columnas a la base de datos...")
        # Add geom columns
        db.execute(text("ALTER TABLE catastro.provincias ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326)"))
        db.execute(text("ALTER TABLE catastro.cantones ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326)"))
        db.execute(text("ALTER TABLE catastro.ciudades ADD COLUMN IF NOT EXISTS geom geometry(MultiPolygon, 4326)"))

        # Add DPA id columns to predio
        db.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS id_provincia INTEGER REFERENCES catastro.provincias(id) ON DELETE SET NULL"))
        db.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS id_canton INTEGER REFERENCES catastro.cantones(id) ON DELETE SET NULL"))
        db.execute(text("ALTER TABLE catastro.predio ADD COLUMN IF NOT EXISTS id_ciudad INTEGER REFERENCES catastro.ciudades(id) ON DELETE SET NULL"))

        db.commit()
        print("Migración DPA completada.")
    except Exception as e:
        db.rollback()
        print(f"Error en migración: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate_dpa()
