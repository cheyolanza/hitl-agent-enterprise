import logging
import time
from functools import wraps

# Configuración de logging enterprise

# Configuración de logging compatible con Streamlit
logger = logging.getLogger("HITL-Enterprise-Frontend")
logger.setLevel(logging.INFO)

# Evitar agregar múltiples handlers si ya existen
if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    file_handler = logging.FileHandler("app_audit.log")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def retry(max_attempts=3, delay=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Error: {e}. Intento {attempts+1}/{max_attempts}")
                    attempts += 1
                    time.sleep(delay)
            logger.critical(f"Fallo permanente en {func.__name__}")
            raise
        return wrapper
    return decorator

# Auditoría simple
def audit_action(user, action, payload=None):
    logger.info(f"AUDIT | user={user} | action={action} | payload={payload}")
