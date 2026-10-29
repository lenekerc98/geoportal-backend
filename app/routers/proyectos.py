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
    if not user.rol or user.rol.nombre.lower() not in ["superadmin", "superadministrador", "admin", "administrador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Administrador para realizar esta acción."
        )

@router.get("", response_model=List[schemas.Proyecto])
@router.get("/", response_model=List[schemas.Proyecto])
def list_proyectos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Lectura dinámica de proyectos según empresa asignada y permisos del usuario
    role_name = ""
    if hasattr(current_user, 'rol') and current_user.rol:
        role_name = str(current_user.rol.nombre).lower()
    elif hasattr(current_user, 'role'):
        role_name = str(current_user.role).lower()

    if role_name in ["superadmin", "superadministrador"]:
        return db.query(Proyecto).filter(Proyecto.estado == 'Activo').order_by(Proyecto.id).all()
    elif role_name in ["admin", "administrador"] and getattr(current_user, 'id_empresa', None):
        return db.query(Proyecto).filter(Proyecto.empresas.any(id=current_user.id_empresa), Proyecto.estado == 'Activo').order_by(Proyecto.id).all()
    else:
        # Si tiene proyectos asignados explícitamente en seguridad.usuario_proyecto
        user_projs = getattr(current_user, 'proyectos', [])
        if user_projs and len(user_projs) > 0:
            return [p for p in user_projs if getattr(p, 'estado', 'Activo') == 'Activo']

        # Si tiene empresa asignada, proyectos activos asociados a dicha empresa
        user_emp = getattr(current_user, 'id_empresa', None)
        if not user_emp and hasattr(current_user, 'empresa_id'):
            user_emp = getattr(current_user, 'empresa_id', None)

        if user_emp:
            return db.query(Proyecto).filter(Proyecto.empresas.any(id=user_emp), Proyecto.estado == 'Activo').order_by(Proyecto.id).all()

        return []

@router.post("", response_model=schemas.Proyecto)
@router.post("/", response_model=schemas.Proyecto)
def create_proyecto(proyecto: schemas.ProyectoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    cur_role = current_user.rol.nombre.lower() if current_user.rol else ""
    if cur_role in ["admin", "administrador"]:
        # Si es Administrador, se vincula automáticamente a su empresa asignada sin obligarlo a seleccionarla
        if not proyecto.empresas_ids:
            if getattr(current_user, 'id_empresa', None):
                proyecto.empresas_ids = [current_user.id_empresa]
        elif getattr(current_user, 'id_empresa', None) and current_user.id_empresa not in proyecto.empresas_ids:
            proyecto.empresas_ids = [current_user.id_empresa]
        
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
