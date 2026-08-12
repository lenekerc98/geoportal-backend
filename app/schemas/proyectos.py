from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProyectoBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    estado: Optional[str] = "Activo"
    empresas_ids: Optional[list[int]] = []
    map_lat: Optional[float] = -1.5833
    map_lng: Optional[float] = -79.4667
    map_zoom: Optional[int] = 14
    map_basemap: Optional[str] = "osm"

class ProyectoCreate(ProyectoBase):
    pass

class ProyectoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    estado: Optional[str] = None
    empresas_ids: Optional[list[int]] = None
    map_lat: Optional[float] = None
    map_lng: Optional[float] = None
    map_zoom: Optional[int] = None
    map_basemap: Optional[str] = None

class Proyecto(ProyectoBase):
    id: int
    fecha_creacion: datetime

    class Config:
        from_attributes = True
