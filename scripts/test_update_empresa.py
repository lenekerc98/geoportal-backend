import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.user import Empresa, Proyecto
from app.schemas.empresa import EmpresaUpdate

db = SessionLocal()

# Find the first empresa
db_empresa = db.query(Empresa).first()
if not db_empresa:
    print("No empresas found.")
    sys.exit(0)

print(f"Testing update for empresa {db_empresa.id}")

emp_update = EmpresaUpdate(
    nombre=db_empresa.nombre,
    ruc=db_empresa.ruc,
    proyectos_ids=[]
)

try:
    if emp_update.nombre is not None: db_empresa.nombre = emp_update.nombre
    if emp_update.ruc is not None: db_empresa.ruc = emp_update.ruc
    if emp_update.proyectos_ids is not None:
        proyectos = db.query(Proyecto).filter(Proyecto.id.in_(emp_update.proyectos_ids)).all()
        db_empresa.proyectos = proyectos
    
    db.commit()
    db.refresh(db_empresa)
    print("Update successful!")
except Exception as e:
    print("Error during update:")
    import traceback
    traceback.print_exc()
finally:
    db.close()
