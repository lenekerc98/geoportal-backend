import os
import sys
from sqlalchemy import text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.database import SessionLocal

load_dotenv()

def migrate():
    db = SessionLocal()
    try:
        # Verifica si la tabla existe en catastro
        check_query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE  table_schema = 'catastro'
                AND    table_name   = 'configuracion_smtp'
            );
        """)
        exists = db.execute(check_query).scalar()
        
        if exists:
            # Asegurar que el esquema seguridad exista (por si acaso)
            db.execute(text("CREATE SCHEMA IF NOT EXISTS seguridad;"))
            
            # Mover la tabla
            print("Moviendo la tabla configuracion_smtp de catastro a seguridad...")
            db.execute(text("ALTER TABLE catastro.configuracion_smtp SET SCHEMA seguridad;"))
            db.commit()
            print("Migración completada exitosamente.")
        else:
            print("La tabla configuracion_smtp ya no está en el esquema catastro o no existe.")
            
    except Exception as e:
        print(f"Error en la migración: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
