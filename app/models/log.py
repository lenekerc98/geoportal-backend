from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
import datetime

class Log(Base):
    __tablename__ = "logs"
    __table_args__ = {'schema': 'seguridad'}

    id_log = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(20), nullable=False) # 'INFO', 'ERROR', 'WARNING'
    accion = Column(String(100), nullable=False) # 'LOGIN', 'CREATE', etc.
    descripcion = Column(Text, nullable=False)
    id_usuario = Column(Integer, ForeignKey("seguridad.usuarios.id_usuario"), nullable=True)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

    usuario = relationship("Usuario")
