from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Numeric, Table
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

empresa_proyecto = Table(
    'empresa_proyecto',
    Base.metadata,
    Column('empresa_id', Integer, ForeignKey('catastro.empresa.id', ondelete='CASCADE'), primary_key=True),
    Column('proyecto_id', Integer, ForeignKey('catastro.proyecto.id', ondelete='CASCADE'), primary_key=True),
    schema='catastro'
)

usuario_proyecto = Table(
    'usuario_proyecto',
    Base.metadata,
    Column('usuario_id', Integer, ForeignKey('seguridad.usuarios.id_usuario', ondelete='CASCADE'), primary_key=True),
    Column('proyecto_id', Integer, ForeignKey('catastro.proyecto.id', ondelete='CASCADE'), primary_key=True),
    schema='seguridad'
)

class Proyecto(Base):
    __tablename__ = "proyecto"
    __table_args__ = {'schema': 'catastro'}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    descripcion = Column(String, nullable=True)
    estado = Column(String(50), default='Activo')
    map_lat = Column(Numeric(15,8), default=-1.5833)
    map_lng = Column(Numeric(15,8), default=-79.4667)
    map_zoom = Column(Integer, default=14)
    map_basemap = Column(String(100), default='osm')
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    empresas = relationship("Empresa", secondary=empresa_proyecto, back_populates="proyectos")

    @property
    def empresas_ids(self):
        return [e.id for e in self.empresas]


class Empresa(Base):
    __tablename__ = "empresa"
    __table_args__ = {'schema': 'catastro'}

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    ruc = Column(String(20), unique=True, nullable=True)
    telefono = Column(String(50), nullable=True)
    correo = Column(String(100), nullable=True)
    direccion = Column(String, nullable=True)
    provincia = Column(String(100), nullable=True)
    canton = Column(String(100), nullable=True)
    ciudad = Column(String(100), nullable=True)
    sector = Column(String(50), nullable=True)
    parametros = Column(JSON, nullable=True, default=dict)
    logo_url = Column(String(500), nullable=True)
    bandera_url = Column(String(500), nullable=True)
    nombre_alcalde = Column(String(200), nullable=True)
    nombre_director = Column(String(200), nullable=True)
    sbu_actual = Column(Numeric(10,2), nullable=True)
    valor_m2_urbano = Column(Numeric(10,2), nullable=True)
    valor_m2_rural = Column(Numeric(10,2), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="empresa")
    proyectos = relationship("Proyecto", secondary=empresa_proyecto, back_populates="empresas")

    @property
    def proyectos_ids(self):
        return [p.id for p in self.proyectos]

class Rol(Base):
    __tablename__ = "roles"
    __table_args__ = {'schema': 'seguridad'}

    id_rol = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String)
    permisos = Column(JSON, nullable=True)

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
    nombres = Column(String(100), nullable=True)
    apellidos = Column(String(100), nullable=True)
    cedula = Column(String(20), nullable=True)
    correo = Column(String(100), nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    rol = relationship("Rol", back_populates="usuarios")
    empresa = relationship("Empresa", back_populates="usuarios")
    proyectos = relationship("Proyecto", secondary=usuario_proyecto, backref="usuarios_asignados")

    @property
    def nombres_completos(self):
        n = self.nombres or ""
        a = self.apellidos or ""
        if n and a:
            return f"{n} {a}"
        return n or a or ""
