import sys
import os

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
query = text("SELECT fecha, tipo, accion, descripcion FROM seguridad.logs ORDER BY fecha DESC LIMIT 5")
res = db.execute(query).fetchall()

for r in res:
    print(r)
db.close()
