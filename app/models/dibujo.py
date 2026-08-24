from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.sql import func
from geoalchemy2 import Geometry
from app.core.database import Base

class CapaDibujo(Base):
    __tablename__ = "capa_dibujo"
    __table_args__ = {"schema": "catastro"}

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False) # 'Point', 'LineString', 'Polygon'
    geom = Column(Geometry(geometry_type='GEOMETRY', srid=32717))
    usuario_id = Column(Integer, ForeignKey('seguridad.usuarios.id_usuario', ondelete='SET NULL'))
    fecha_creacion = Column(DateTime, default=func.now())
