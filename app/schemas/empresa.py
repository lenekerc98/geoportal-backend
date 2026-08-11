from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class EmpresaBase(BaseModel):
    nombre: str
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    provincia: Optional[str] = None
    canton: Optional[str] = None
    ciudad: Optional[str] = None
    sector: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    bandera_url: Optional[str] = None
    nombre_alcalde: Optional[str] = None
    nombre_director: Optional[str] = None
    sbu_actual: Optional[float] = None
    valor_m2_urbano: Optional[float] = None
    valor_m2_rural: Optional[float] = None
    proyectos_ids: Optional[list[int]] = []

class EmpresaCreate(EmpresaBase):
    pass

class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    ruc: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    direccion: Optional[str] = None
    provincia: Optional[str] = None
    canton: Optional[str] = None
    ciudad: Optional[str] = None
    sector: Optional[str] = None
    parametros: Optional[Dict[str, Any]] = None
    logo_url: Optional[str] = None
    bandera_url: Optional[str] = None
    nombre_alcalde: Optional[str] = None
    nombre_director: Optional[str] = None
    sbu_actual: Optional[float] = None
    valor_m2_urbano: Optional[float] = None
    valor_m2_rural: Optional[float] = None
    proyectos_ids: Optional[list[int]] = None

class Empresa(EmpresaBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
