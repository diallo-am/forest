import os
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()
class Config:
    """Configuration de l'application"""
    HOST = '0.0.0.0'
    PORT = 5000
    # Base de données
    DB_HOST = 'localhost'
    DB_USER = 'iot_user'
    DB_PASSWORD = 'iot1234567890!'
    DB_NAME = 'iot_db'
    
    # Flask
    SECRET_KEY = 'dev-secret-key-in-production'
    DEBUG = True
    
    # JWT
    JWT_SECRET_KEY = 'jwt_secret_key_change_in_production_12345'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # Email (SMTP)
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME', 'alertesforet@gmail.com')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', 'eems uhad alva mkhp')
    SMTP_FROM = os.getenv('SMTP_FROM', 'iot-system@localhost')
    
    # Alertes
    ALERT_CHECK_INTERVAL = 60  # secondes
    MAX_ALERTS_PER_HOUR = 20   # limite d'emails par heure
    
    # Logs
    LOG_FILE = 'logs/app.log'
    LOG_LEVEL = 'INFO'
    
    # Sécurité
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max
    ALLOWED_EXTENSIONS = {'json', 'csv'}
