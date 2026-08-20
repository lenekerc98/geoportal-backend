import os
import smtplib
import threading
from email.message import EmailMessage
from sqlalchemy.orm import Session
from app.models.log import Log
from app.core.database import SessionLocal
from cryptography.fernet import Fernet

def get_fernet():
    key = os.getenv("SMTP_SECRET_KEY", "b41M_M2qS7_b7zXh5V_N9C_M8YqP1y_p-L5Z7b2qP_o=")
    return Fernet(key.encode())

def enviar_correo_alerta(asunto: str, cuerpo: str):
    """Envía un correo usando SMTP leyendo config de BD"""
    db = SessionLocal()
    try:
        from app.models.config import ConfiguracionSMTP
        config = db.query(ConfiguracionSMTP).filter(ConfiguracionSMTP.is_active == True).first()
        if not config:
            # Fallback to env
            smtp_server = os.getenv("SMTP_SERVER")
            smtp_port = int(os.getenv("SMTP_PORT", "587"))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            destinatarios = os.getenv("ALERT_EMAIL_TO")
        else:
            smtp_server = config.smtp_server
            smtp_port = config.smtp_port
            smtp_user = config.smtp_user
            f = get_fernet()
            smtp_password = f.decrypt(config.smtp_password.encode()).decode()
            destinatarios = config.alert_email_to
            
        if not all([smtp_server, smtp_user, smtp_password, destinatarios]):
            print("Faltan variables SMTP. No se envía correo.")
            return

        msg = EmailMessage()
        msg.set_content(cuerpo)
        msg['Subject'] = asunto
        msg['From'] = smtp_user
        
        dests = [d.strip() for d in destinatarios.split(",")]
        msg['To'] = ", ".join(dests)

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    except Exception as e:
        print(f"Error al enviar correo de alerta: {e}")
    finally:
        db.close()

def log_audit(db: Session, tipo: str, accion: str, descripcion: str, id_usuario: int = None, enviar_alerta: bool = False):
    """Guarda el log y dispara alerta si es error crítico"""
    try:
        nuevo_log = Log(
            tipo=tipo,
            accion=accion,
            descripcion=descripcion,
            id_usuario=id_usuario
        )
        db.add(nuevo_log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error al escribir en la bitácora: {e}")
        
    # Disparar alerta automática si es un error
    if tipo in ["ERROR", "CRITICAL"] or enviar_alerta:
        asunto = f"[{tipo}] Alerta Catastro: {accion}"
        cuerpo = f"Se registró una falla en el servidor.\n\nAcción: {accion}\nUsuario ID: {id_usuario or 'Desconocido'}\n\nDetalles del error:\n{descripcion}"
        threading.Thread(target=enviar_correo_alerta, args=(asunto, cuerpo), daemon=True).start()
