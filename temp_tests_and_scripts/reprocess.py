import os
from app.core.database import SessionLocal
from app.core.ortofoto_service import procesar_ortofoto_background

def reprocess():
    db = SessionLocal()
    try:
        ruta = r"C:\LNCZ\proyecto-catastro-2026\Ortofotos\Complementos\2026\07\Ortofoto_Completa.tif"
        print(f"Procesando {ruta}...")
        procesar_ortofoto_background("test-task-123", ruta, db)
        print("Procesamiento terminado.")
    finally:
        db.close()

if __name__ == "__main__":
    reprocess()
