from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import Empresa
from app.routers.users import get_current_user
from app.models.user import Usuario
from app import schemas

router = APIRouter(
    prefix="/empresas",
    tags=["Empresas"]
)

def is_superadmin(user: Usuario):
    if not user.rol or user.rol.nombre.lower() != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Superadmin para realizar esta acción."
        )

def is_superadmin_or_admin(user: Usuario):
    if not user.rol or user.rol.nombre.lower() not in ["superadmin", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere rol de Administrador para realizar esta acción."
        )

@router.get("/", response_model=List[schemas.Empresa])
def list_empresas(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    if current_user.rol.nombre.lower() == "admin":
        return db.query(Empresa).filter(Empresa.id == current_user.id_empresa).all()
    return db.query(Empresa).all()

@router.post("/", response_model=schemas.Empresa)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    # Check if ruc exists
    if empresa.ruc:
        existing = db.query(Empresa).filter(Empresa.ruc == empresa.ruc).first()
        if existing:
            raise HTTPException(status_code=400, detail="El RUC ya está registrado para otra empresa.")
            
    db_empresa = Empresa(**empresa.model_dump())
    db.add(db_empresa)
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@router.put("/{empresa_id}", response_model=schemas.Empresa)
def update_empresa(empresa_id: int, emp: schemas.EmpresaUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    
    if current_user.rol.nombre.lower() == "admin" and current_user.id_empresa != empresa_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar otra empresa.")
        
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    
    if emp.nombre is not None: db_empresa.nombre = emp.nombre
    if emp.ruc is not None: db_empresa.ruc = emp.ruc
    if emp.telefono is not None: db_empresa.telefono = emp.telefono
    if emp.correo is not None: db_empresa.correo = emp.correo
    if emp.direccion is not None: db_empresa.direccion = emp.direccion
    if emp.parametros is not None: db_empresa.parametros = emp.parametros
    
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_empresa(empresa_id: int, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
        
    db.delete(db_empresa)
    db.commit()
    return None
