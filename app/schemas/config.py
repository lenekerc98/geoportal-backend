from pydantic import BaseModel
from typing import Optional

class ConfiguracionSMTPBase(BaseModel):
    smtp_server: str
    smtp_port: int
    smtp_user: str
    alert_email_to: str
    is_active: bool = True

class ConfiguracionSMTPCreate(ConfiguracionSMTPBase):
    smtp_password: str

class ConfiguracionSMTPUpdate(ConfiguracionSMTPBase):
    smtp_password: Optional[str] = None

class ConfiguracionSMTPResponse(ConfiguracionSMTPBase):
    id: int
    
    class Config:
        orm_mode = True
        from_attributes = True
