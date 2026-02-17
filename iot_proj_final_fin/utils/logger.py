import logging
import os
from logging.handlers import RotatingFileHandler
from config import Config
from database import db

def setup_logger():
    """Configure le système de logging"""
    # Créer le dossier logs s'il n'existe pas
    os.makedirs('logs', exist_ok=True)
    
    # Configuration du logger
    logger = logging.getLogger('iot_app')
    logger.setLevel(getattr(logging, Config.LOG_LEVEL))
    
    # Handler fichier avec rotation
    file_handler = RotatingFileHandler(
        Config.LOG_FILE,
        maxBytes=10485760,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)s: %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_to_database(niveau, action, message, noeud_id=None, details=None):
    """Enregistre un log dans la base de données"""
    try:
        query = """
            INSERT INTO logs (noeud_id, niveau, action, message, adresse_ip, details)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        ip = request.remote_addr if has_request_context() else None
        db.execute_query(query, (noeud_id, niveau, action, message, ip, details))
    except Exception as e:
        print(f"Erreur lors de l'enregistrement du log: {e}")

logger = setup_logger()
