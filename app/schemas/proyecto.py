from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProyectoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None

class ProyectoCreate(ProyectoBase):
    pass

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None

class Proyecto(ProyectoBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
