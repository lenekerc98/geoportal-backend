from sqlalchemy import Column, Integer, String, Boolean, Text
from app.core.database import Base

class ConfiguracionSMTP(Base):
    __tablename__ = "configuracion_smtp"
    __table_args__ = {"schema": "catastro"}

    id = Column(Integer, primary_key=True, index=True)
    smtp_server = Column(String(255), nullable=False)
    smtp_port = Column(Integer, nullable=False, default=587)
    smtp_user = Column(String(255), nullable=False)
    smtp_password = Column(String(255), nullable=False)
    alert_email_to = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
