from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import Proyecto
from app.routers.users import get_current_user
from app.models.user import Usuario
from app import schemas

router = APIRouter(
    prefix="/proyectos",
    tags=["Proyectos"]
)

def is_superadmin(user: Usuario):
    if not user.rol or user.rol.nombre.lower() != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Superadmin para realizar esta acción."
        )

@router.get("", response_model=List[schemas.Proyecto])
@router.get("/", response_model=List[schemas.Proyecto])
def list_proyectos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    return db.query(Proyecto).all()

@router.post("", response_model=schemas.Proyecto)
@router.post("/", response_model=schemas.Proyecto)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    db_proyecto = Proyecto(**proyecto.model_dump())
    db.add(db_proyecto)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.put("/{proyecto_id}", response_model=schemas.Proyecto)
def update_proyecto(proyecto_id: int, p: schemas.ProyectoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    db_proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
    
    if p.nombre is not None: db_proyecto.nombre = p.nombre
    if p.descripcion is not None: db_proyecto.descripcion = p.descripcion
    
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proyecto(proyecto_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    db_proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    db.delete(db_proyecto)
    db.commit()
    return None
