from sqlalchemy.orm import Session
from app.models.log import Log

def log_audit(db: Session, tipo: str, accion: str, descripcion: str, id_usuario: int = None):
    """
    Registra una acción o error en la tabla de bitácora (logs) de PostgreSQL.
    - tipo: 'INFO', 'ERROR', 'WARNING'
    - accion: Ej. 'LOGIN', 'CREAR_PREDIO', 'ELIMINAR_ORTOFOTO'
    - descripcion: Detalles de la acción o el mensaje de error.
    - id_usuario: Opcional. ID del usuario que ejecutó la acción.
    """
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
        # En caso de que el logger falle, no deberíamos tumbar la aplicación
        db.rollback()
        print(f"Error al escribir en la bitácora: {e}")
