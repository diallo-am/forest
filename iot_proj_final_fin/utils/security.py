import secrets
import hashlib
import bcrypt
from functools import wraps
from flask import request, jsonify

def generate_api_key(prefix=''):
    """Génère une clé API sécurisée"""
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}" if prefix else random_part

def hash_password(password):
    """Hash un mot de passe avec bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password, hashed):
    """Vérifie un mot de passe"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def hash_api_key(api_key):
    """Hash une clé API pour comparaison"""
    return hashlib.sha256(api_key.encode()).hexdigest()
