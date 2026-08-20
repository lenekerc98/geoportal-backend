from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.routers.users import get_current_user
from app.models.config import ConfiguracionSMTP
from app.schemas.config import ConfiguracionSMTPResponse, ConfiguracionSMTPUpdate, ConfiguracionSMTPCreate
from cryptography.fernet import Fernet
import os

router = APIRouter(prefix="/configuracion", tags=["Configuracion"])

def get_fernet():
    key = os.getenv("SMTP_SECRET_KEY", "b41M_M2qS7_b7zXh5V_N9C_M8YqP1y_p-L5Z7b2qP_o=")
    return Fernet(key.encode())

@router.get("/smtp", response_model=ConfiguracionSMTPResponse)
def get_smtp_config(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Solo superadmin debería poder ver esto
    config = db.query(ConfiguracionSMTP).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuración SMTP no encontrada")
    return config

@router.put("/smtp", response_model=ConfiguracionSMTPResponse)
def update_smtp_config(data: ConfiguracionSMTPUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    config = db.query(ConfiguracionSMTP).first()
    f = get_fernet()
    
    if not config:
        # Create
        config = ConfiguracionSMTP(
            smtp_server=data.smtp_server,
            smtp_port=data.smtp_port,
            smtp_user=data.smtp_user,
            smtp_password=f.encrypt(data.smtp_password.encode()).decode() if data.smtp_password else "",
            alert_email_to=data.alert_email_to,
            is_active=data.is_active
        )
        db.add(config)
    else:
        # Update
        config.smtp_server = data.smtp_server
        config.smtp_port = data.smtp_port
        config.smtp_user = data.smtp_user
        config.alert_email_to = data.alert_email_to
        config.is_active = data.is_active
        if data.smtp_password:
            config.smtp_password = f.encrypt(data.smtp_password.encode()).decode()
            
    db.commit()
    db.refresh(config)
    return config
