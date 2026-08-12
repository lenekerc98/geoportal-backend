from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class RolSchema(BaseModel):
    id_rol: int
    nombre: str
    descripcion: Optional[str] = None
    permisos: Optional[dict] = None

    class Config:
        from_attributes = True

class RolUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    permisos: Optional[dict] = None

class UsuarioBase(BaseModel):
    username: str
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    cedula: Optional[str] = None
    correo: Optional[str] = None

class UsuarioCreate(UsuarioBase):
    password: str
    id_rol: int
    id_empresa: Optional[int] = None

class Usuario(UsuarioBase):
    id_usuario: int
    id_rol: int
    id_empresa: Optional[int] = None
    activo: bool
    rol: Optional[RolSchema] = None
    nombres_completos: Optional[str] = None

    class Config:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    id_rol: Optional[int] = None
    id_empresa: Optional[int] = None
    activo: Optional[bool] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    cedula: Optional[str] = None
    correo: Optional[str] = None

