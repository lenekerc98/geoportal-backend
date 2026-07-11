from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UsuarioBase(BaseModel):
    username: str

class UsuarioCreate(UsuarioBase):
    password: str
    id_rol: int
    id_empresa: Optional[int] = None

class Usuario(UsuarioBase):
    id_usuario: int
    id_rol: int
    activo: bool

    class Config:
        from_attributes = True

class UsuarioUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    id_rol: Optional[int] = None
    id_empresa: Optional[int] = None
    activo: Optional[bool] = None

