import sys
from app.core.database import SessionLocal
from app.models.user import Proyecto as DBProyecto
from app.schemas.proyectos import Proyecto

try:
    db = SessionLocal()
    proyectos = db.query(DBProyecto).all()
    print("Found projects in DB:", len(proyectos))
    for p in proyectos:
        try:
            schema_p = Proyecto.model_validate(p)
            print("Successfully validated:", schema_p.nombre)
        except Exception as e:
            print("Validation failed for project:", p.id)
            print(e)
except Exception as e:
    print("Error:", e)
