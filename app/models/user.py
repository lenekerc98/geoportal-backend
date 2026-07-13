from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class Proyecto(Base):
    __tablename__ = "proyecto"
    __table_args__ = {'schema': 'catastro'}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    empresas = relationship("Empresa", back_populates="proyecto")

class Empresa(Base):
    __tablename__ = "empresa"
    __table_args__ = {'schema': 'catastro'}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    ruc = Column(String(20), unique=True, nullable=True)
    telefono = Column(String(50), nullable=True)
    correo = Column(String(100), nullable=True)
    direccion = Column(String, nullable=True)
    parametros = Column(JSON, nullable=True, default=dict)
    proyecto_id = Column(Integer, ForeignKey("catastro.proyecto.id"), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="empresa")
    proyecto = relationship("Proyecto", back_populates="empresas")

    usuarios = relationship("Usuario", back_populates="empresa")

class Rol(Base):
    __tablename__ = "roles"
    __table_args__ = {'schema': 'seguridad'}

    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String)

    usuarios = relationship("Usuario", back_populates="rol")

class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = {'schema': 'seguridad'}

    id_usuario = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    id_rol = Column(Integer, ForeignKey("seguridad.roles.id_rol"))
    id_empresa = Column(Integer, ForeignKey("catastro.empresa.id"), nullable=True)
    activo = Column(Boolean, default=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    empresa = relationship("Empresa", back_populates="usuarios")
