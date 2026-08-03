from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import Proyecto, Empresa
from app.routers.users import get_current_user
from app.models.user import Usuario
from app import schemas

router = APIRouter(
    prefix="/proyectos",
    tags=["Proyectos"]
)

def is_superadmin_or_admin(user: Usuario):
    if not user.rol or user.rol.nombre.lower() not in ["superadmin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Administrador para realizar esta acción."
        )

@router.get("", response_model=List[schemas.Proyecto])
@router.get("/", response_model=List[schemas.Proyecto])
def list_proyectos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    if current_user.rol.nombre.lower() == "admin":
        return db.query(Proyecto).filter(Proyecto.empresa_id == current_user.id_empresa).all()
    return db.query(Proyecto).all()

@router.post("", response_model=schemas.Proyecto)
@router.post("/", response_model=schemas.Proyecto)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    if current_user.rol.nombre.lower() == "admin" and proyecto.empresa_id != current_user.id_empresa:
        raise HTTPException(status_code=403, detail="No tienes permisos para crear proyectos en otra empresa.")
        
    db_proyecto = Proyecto(**proyecto.model_dump())
    db.add(db_proyecto)
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.put("/{proyecto_id}", response_model=schemas.Proyecto)
def update_proyecto(proyecto_id: int, proj: schemas.ProyectoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    db_proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    if current_user.rol.nombre.lower() == "admin" and db_proyecto.empresa_id != current_user.id_empresa:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar este proyecto.")
    
    update_data = proj.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_proyecto, key, value)
    
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proyecto(proyecto_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    db_proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    if current_user.rol.nombre.lower() == "admin" and db_proyecto.empresa_id != current_user.id_empresa:
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar este proyecto.")
        
    db.delete(db_proyecto)
    db.commit()
    return None
