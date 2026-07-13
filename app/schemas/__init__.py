from app.schemas.user import Token, TokenData, UsuarioBase, UsuarioCreate, Usuario, UsuarioUpdate, UsuarioLogin, Rol
from app.schemas.gis import (
    Posesionario, PosesionarioBase, Vertice, VerticeCreate, Lindero, LineaLindero, LineaLinderoCreate, Predio, 
    PredioDetalleEspacial, GeoJSONFeatureCollection,
    CodigoCatastral, CodigoCatastralBase, PredioCreate, PredioUpdate, CatalogoOrtofoto, OrtofotoProgreso
)
from app.schemas.empresa import Empresa, EmpresaCreate, EmpresaUpdate, EmpresaBase
from app.schemas.proyecto import Proyecto, ProyectoCreate, ProyectoUpdate
