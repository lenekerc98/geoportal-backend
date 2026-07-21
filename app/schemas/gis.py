from pydantic import BaseModel
from typing import List, Optional, Any

# --- Modelos Relacionales Geográficos (WKT / Atributos) ---

class PosesionarioBase(BaseModel):
    cedula: str
    nombre: str

class Posesionario(PosesionarioBase):
    id: int

    class Config:
        from_attributes = True

class CodigoCatastralBase(BaseModel):
    codigo: str
    activo: Optional[bool] = True
    posesionario_id: Optional[int] = None

class CodigoCatastral(CodigoCatastralBase):
    fecha_creacion: Optional[Any] = None
    cedula_posesionario: Optional[str] = None
    nombre_posesionario: Optional[str] = None

    class Config:
        from_attributes = True

class VerticeBase(BaseModel):
    codigo: str

class Vertice(VerticeBase):
    id: int
    predio_id: int
    cod_catastral: Optional[str] = None
    coord_x: float
    coord_y: float
    geom_wkt: str  # Representación en texto: "POINT(x y)"

    class Config:
        from_attributes = True

class LinderoBase(BaseModel):
    longitud: float
    rumbo: Optional[str] = None
    colindante: Optional[str] = None
    tramo: Optional[str] = None

class Lindero(LinderoBase):
    id: int
    predio_id: int
    cod_catastral: Optional[str] = None
    geom_wkt: str  # Representación en texto: "LINESTRING(x1 y1, x2 y2)"

    class Config:
        from_attributes = True

class PredioBase(BaseModel):
    cod_catastral: Optional[str] = None
    area_ha: float

class PredioCreate(BaseModel):
    posesionario_id: Optional[int] = None
    geom_geojson: dict  # Un diccionario GeoJSON Geometry válido, ej: {"type": "Polygon", "coordinates": [[[lng, lat], ...]]}
    cod_catastral: Optional[str] = None
    es_utm: Optional[bool] = False
    colindantes: Optional[List[str]] = None

class PredioUpdate(BaseModel):
    posesionario_id: Optional[int] = None
    geom_geojson: Optional[dict] = None
    cod_catastral: Optional[str] = None
    estado: Optional[str] = None
    es_utm: Optional[bool] = False
    colindantes: Optional[List[str]] = None

class Predio(PredioBase):
    id: int
    posesionario_id: Optional[int] = None
    nombre_posesionario: Optional[str] = None
    cedula: Optional[str] = None
    estado: Optional[str] = None
    fecha_creacion: Optional[Any] = None
    fecha_baja: Optional[Any] = None
    predio_padre_id: Optional[int] = None
    geom_wkt: str  # Representación en texto: "POLYGON((x1 y1, ...))"

    class Config:
        from_attributes = True

# Modelo para retornar la ficha catastral geoespacial completa de un predio
class PredioDetalleEspacial(BaseModel):
    predio: Predio
    vertices: List[Vertice]
    linderos: List[Lindero]


# --- Modelos Estructura GeoJSON para Frontend ---

class GeoJSONGeometry(BaseModel):
    type: str  # 'Point', 'LineString', 'Polygon'
    coordinates: Any  # Lista de coordenadas según el tipo de geometría

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: dict
    id: Optional[int] = None

class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature]

class ProcesarOrtofotoRequest(BaseModel):
    ruta_archivo: str
