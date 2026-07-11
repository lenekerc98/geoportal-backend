from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: str
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None

class Empresa(EmpresaBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
