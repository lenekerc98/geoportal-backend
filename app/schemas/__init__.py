from app.schemas.user import Token, TokenData, UsuarioBase, UsuarioCreate, Usuario, UsuarioUpdate
from app.schemas.gis import (
    Posesionario, PosesionarioBase, Vertice, Lindero, Predio, 
    PredioDetalleEspacial, GeoJSONFeatureCollection,
    CodigoCatastral, CodigoCatastralBase, PredioCreate, PredioUpdate
)
from app.schemas.empresa import Empresa, EmpresaCreate, EmpresaUpdate, EmpresaBase
from app.schemas.proyecto import Proyecto, ProyectoCreate, ProyectoUpdate
