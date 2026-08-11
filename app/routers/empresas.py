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

@router.get("", response_model=List[schemas.Empresa])
@router.get("/", response_model=List[schemas.Empresa])
def list_empresas(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin_or_admin(current_user)
    if current_user.rol.nombre.lower() == "admin":
        return db.query(Empresa).filter(Empresa.id == current_user.id_empresa).all()
    return db.query(Empresa).all()

@router.post("", response_model=schemas.Empresa)
@router.post("/", response_model=schemas.Empresa)
def create_empresa(empresa: schemas.EmpresaCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    is_superadmin(current_user)
    
    # Check if ruc exists
    if empresa.ruc:
        existing = db.query(Empresa).filter(Empresa.ruc == empresa.ruc).first()
        if existing:
            raise HTTPException(status_code=400, detail="El RUC ya está registrado para otra empresa.")
            
    empresa_data = empresa.model_dump(exclude={'proyectos_ids'})
    db_empresa = Empresa(**empresa_data)
    if empresa.proyectos_ids:
        from app.models.user import Proyecto
        proyectos = db.query(Proyecto).filter(Proyecto.id.in_(empresa.proyectos_ids)).all()
        db_empresa.proyectos.extend(proyectos)
    
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
    if emp.provincia is not None: db_empresa.provincia = emp.provincia
    if emp.canton is not None: db_empresa.canton = emp.canton
    if emp.ciudad is not None: db_empresa.ciudad = emp.ciudad
    if emp.sector is not None: db_empresa.sector = emp.sector
    if emp.parametros is not None: db_empresa.parametros = emp.parametros
    if emp.logo_url is not None: db_empresa.logo_url = emp.logo_url
    if emp.bandera_url is not None: db_empresa.bandera_url = emp.bandera_url
    if emp.nombre_alcalde is not None: db_empresa.nombre_alcalde = emp.nombre_alcalde
    if emp.nombre_director is not None: db_empresa.nombre_director = emp.nombre_director
    if emp.sbu_actual is not None: db_empresa.sbu_actual = emp.sbu_actual
    if emp.valor_m2_urbano is not None: db_empresa.valor_m2_urbano = emp.valor_m2_urbano
    if emp.valor_m2_rural is not None: db_empresa.valor_m2_rural = emp.valor_m2_rural
    
    if emp.proyectos_ids is not None:
        from app.models.user import Proyecto
        proyectos = db.query(Proyecto).filter(Proyecto.id.in_(emp.proyectos_ids)).all()
        db_empresa.proyectos = proyectos
    
    db.commit()
    db.refresh(db_empresa)
    return db_empresa

import os
import shutil
from fastapi import UploadFile, File

@router.post("/{empresa_id}/upload-images", response_model=schemas.Empresa)
def upload_empresa_images(
    empresa_id: int, 
    logo: UploadFile = File(None),
    bandera: UploadFile = File(None),
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_user)
):
    is_superadmin_or_admin(current_user)
    if current_user.rol.nombre.lower() == "admin" and current_user.id_empresa != empresa_id:
        raise HTTPException(status_code=403, detail="No tienes permisos para editar otra empresa.")
        
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    uploads_dir = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "empresas")
    os.makedirs(uploads_dir, exist_ok=True)

    if logo:
        filename = f"logo_{empresa_id}_{logo.filename}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(logo.file, buffer)
        db_empresa.logo_url = f"/uploads/empresas/{filename}"

    if bandera:
        filename = f"bandera_{empresa_id}_{bandera.filename}"
        file_path = os.path.join(uploads_dir, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(bandera.file, buffer)
        db_empresa.bandera_url = f"/uploads/empresas/{filename}"

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
