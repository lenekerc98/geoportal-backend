import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.user import Empresa

db = SessionLocal()
e = db.query(Empresa).filter(Empresa.id == 2).first()
if e:
    print("Logo URL length:", len(e.logo_url) if e.logo_url else "None")
    print("Logo URL preview:", e.logo_url[:50] if e.logo_url else "None")
else:
    print("Empresa 2 no encontrada.")
