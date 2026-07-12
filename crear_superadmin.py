import os
import sys

# Añadir el directorio actual al PYTHONPATH para que reconozca "app"
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.models.user import Rol, Usuario, Empresa
from app.core.security import get_password_hash

def seed_db():
    db = SessionLocal()
    try:
        # 1. Crear roles básicos si no existen
        roles_necesarios = [
            (1, "Superadmin", "Administrador principal del sistema con acceso total"),
            (2, "Admin", "Administrador de empresa"),
            (3, "Usuario", "Usuario estándar del sistema")
        ]
        
        for id_rol, nombre, desc in roles_necesarios:
            rol_existente = db.query(Rol).filter(Rol.id_rol == id_rol).first()
            if not rol_existente:
                nuevo_rol = Rol(id_rol=id_rol, nombre=nombre, descripcion=desc)
                db.add(nuevo_rol)
                print(f"Rol {nombre} creado.")

        # 2. Crear empresa principal si no existe
        empresa_existente = db.query(Empresa).filter(Empresa.nombre == "Catastro Principal").first()
        if not empresa_existente:
            empresa_existente = Empresa(
                nombre="Catastro Principal",
                ruc="0000000000001",
                correo="admin@catastro.local",
                parametros={}
            )
            db.add(empresa_existente)
            db.flush() # Para obtener el ID
            print("Empresa 'Catastro Principal' creada.")

        # 3. Crear usuario Icedeno
        usuario_existente = db.query(Usuario).filter(Usuario.username == "lcedeno").first()
        if not usuario_existente:
            admin_user = Usuario(
                username="lcedeno",
                password_hash=get_password_hash("lenekerc98"),
                id_rol=1, # Superadmin
                id_empresa=None, # Superadmin puede ver todo
                activo=True
            )
            db.add(admin_user)
            print("Usuario 'lcedeno' (Superadmin) creado correctamente.")
            
            # También intentar crearlo en el motor PostgreSQL real para QGIS
            try:
                db.execute(text(f"CREATE USER lcedeno WITH PASSWORD 'lenekerc98'"))
                db.execute(text(f"ALTER USER lcedeno LOGIN SUPERUSER"))
                print("Usuario de base de datos 'lcedeno' creado y con permisos de superusuario.")
            except Exception as e:
                print(f"Nota: El usuario PostgreSQL 'lcedeno' ya existe o hubo un aviso: {e}")

        db.commit()
        print("\n¡Base de datos inicializada con éxito! Ya puedes iniciar sesión.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    print("Conectando a la base de datos (revisa tu .env)...")
    seed_db()
