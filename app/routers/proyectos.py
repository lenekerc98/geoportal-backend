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
        return db.query(Proyecto).filter(Proyecto.empresas.any(id=current_user.id_empresa)).all()
    return db.query(Proyecto).all()

@router.post("", response_model=schemas.Proyecto)
@router.post("/", response_model=schemas.Proyecto)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    if current_user.rol.nombre.lower() == "admin" and (not proyecto.empresas_ids or current_user.id_empresa not in proyecto.empresas_ids):
        raise HTTPException(status_code=403, detail="No tienes permisos para crear proyectos sin tu empresa.")
        
    proyecto_data = proyecto.model_dump(exclude={'empresas_ids'})
    db_proyecto = Proyecto(**proyecto_data)
    
    if proyecto.empresas_ids:
        empresas = db.query(Empresa).filter(Empresa.id.in_(proyecto.empresas_ids)).all()
        db_proyecto.empresas.extend(empresas)
        
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
        
    if current_user.rol.nombre.lower() == "admin" and current_user.id_empresa not in [e.id for e in db_proyecto.empresas]:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar este proyecto.")
    
    update_data = proj.model_dump(exclude_unset=True, exclude={'empresas_ids'})
    for key, value in update_data.items():
        setattr(db_proyecto, key, value)
        
    if proj.empresas_ids is not None:
        empresas = db.query(Empresa).filter(Empresa.id.in_(proj.empresas_ids)).all()
        db_proyecto.empresas = empresas
    
    db.commit()
    db.refresh(db_proyecto)
    return db_proyecto

@router.delete("/{proyecto_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proyecto(proyecto_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    db_proyecto = db.query(Proyecto).filter(Proyecto.id == proyecto_id).first()
    if not db_proyecto:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        
    if current_user.rol.nombre.lower() == "admin" and current_user.id_empresa not in [e.id for e in db_proyecto.empresas]:
        raise HTTPException(status_code=403, detail="No tienes permisos para eliminar este proyecto.")
        
    db.delete(db_proyecto)
    db.commit()
    return None
