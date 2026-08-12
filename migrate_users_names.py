from dotenv import load_dotenv
load_dotenv()

from app.core.database import SessionLocal
from sqlalchemy import text

def migrate():
    db = SessionLocal()
    try:
        # Añadir columnas si no existen
        db.execute(text("""
            ALTER TABLE seguridad.usuarios 
            ADD COLUMN IF NOT EXISTS nombres VARCHAR(100),
            ADD COLUMN IF NOT EXISTS apellidos VARCHAR(100),
            ADD COLUMN IF NOT EXISTS cedula VARCHAR(20),
            ADD COLUMN IF NOT EXISTS correo VARCHAR(100);
        """))
        print("Columnas añadidas exitosamente a seguridad.usuarios.")
        db.commit()
    except Exception as ex:
        db.rollback()
        print(f"Migration failed: {ex}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
