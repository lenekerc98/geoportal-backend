import os
from dotenv import load_dotenv

load_dotenv()

comp_dir = os.getenv("DIR_ORTOFOTOS_COMPLEMENTOS")
print("COMP_DIR:", comp_dir)

filename = "Ortofoto_Completa.tif"
nombre_base = os.path.splitext(filename)[0]
vrt_individual = os.path.join(comp_dir, f"{nombre_base}.vrt")
print("VRT PATH:", vrt_individual)
print("EXISTS:", os.path.exists(vrt_individual))

from app.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
q = text("SELECT ruta_completa FROM catastro.ortofotos_catalogo WHERE nombre_archivo = :fname")
result = db.execute(q, {"fname": filename}).fetchone()
print("DB RUTA:", result[0] if result else None)
if result:
    print("DB RUTA EXISTS:", os.path.exists(result[0]))
