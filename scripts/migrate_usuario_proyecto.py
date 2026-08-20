import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal, engine
from app.models.user import Base, Usuario, Proyecto
from sqlalchemy import text

def migrate():
    # 1. Create the new table
    Base.metadata.create_all(bind=engine)
    print("Table usuario_proyecto created (if it didn't exist).")

    db = SessionLocal()
    try:
        # 2. Assign all projects from their company to existing users (who don't have superadmin or admin)
        users = db.query(Usuario).all()
        for u in users:
            rol_name = u.rol.nombre.lower() if u.rol else ""
            if rol_name not in ["superadmin", "superadministrador", "admin"]:
                if getattr(u, 'id_empresa', None) is not None:
                    # Get projects for this company
                    empresa = u.empresa
                    if empresa and empresa.proyectos:
                        u.proyectos = list(empresa.proyectos)
                        print(f"Assigned {len(empresa.proyectos)} projects to user {u.username}")
        db.commit()
        print("Migration completed successfully.")
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
