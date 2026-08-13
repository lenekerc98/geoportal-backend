from app.schemas.user import Token, TokenData, UsuarioBase, UsuarioCreate, Usuario, UsuarioUpdate, RolSchema, RolUpdate
from app.schemas.gis import (
    Posesionario, PosesionarioBase, Vertice, Lindero, Predio, 
    PredioDetalleEspacial, GeoJSONFeatureCollection,
    CodigoCatastral, CodigoCatastralBase, PredioCreate, PredioUpdate, PredioAnguloUpdate
)
from app.schemas.empresa import Empresa, EmpresaCreate, EmpresaUpdate, EmpresaBase
from app.schemas.proyectos import Proyecto, ProyectoCreate, ProyectoUpdate
