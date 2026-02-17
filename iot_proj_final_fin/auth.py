import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from config import Config
from database import db
from utils.logger import logger, log_to_database

def generate_token(user_id, username, role):
    """Génère un JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'role': role,
        'exp': datetime.utcnow() + Config.JWT_ACCESS_TOKEN_EXPIRES,
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm='HS256')
    print(f"Token genere pour {username}, expire dans 30j")
    return token

def verify_token(token):
    """Vérifie un JWT token"""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def verify_api_key(api_key):
    """Vérifie une clé API de noeud"""
    try:
        query = "SELECT id, nom, statut FROM noeuds WHERE api_key = %s AND statut = 'actif'"
        result = db.execute_query(query, (api_key,))
        
        if result:
            # Mettre à jour la dernière connexion
            update_query = "UPDATE noeuds SET derniere_connexion = NOW() WHERE id = %s"
            db.execute_query(update_query, (result[0]['id'],))
            return result[0]
        return None
    except Exception as e:
        logger.error(f"Erreur vérification API key: {e}")
        return None

def token_required(f):
    """Décorateur pour protéger les routes avec JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Vérifier le header Authorization
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(" ")[1]  # Bearer TOKEN
            except IndexError:
                return jsonify({'error': 'Format de token invalide'}), 401
        
        if not token:
            return jsonify({'error': 'Token manquant'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Token invalide ou expiré'}), 401
        
        return f(payload, *args, **kwargs)
    
    return decorated

def api_key_required(f):
    """Décorateur pour protéger les routes avec API Key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = None
        
        # Vérifier le header X-API-Key
        if 'X-API-Key' in request.headers:
            api_key = request.headers['X-API-Key']
        # Ou dans le body JSON
        elif request.is_json:
            api_key = request.json.get('api_key')
        
        if not api_key:
            log_to_database('warning', 'api_auth_failed', 'Clé API manquante')
            return jsonify({'error': 'Clé API manquante'}), 401
        
        noeud = verify_api_key(api_key)
        if not noeud:
            log_to_database('warning', 'api_auth_failed', f'Clé API invalide: {api_key[:10]}...')
            return jsonify({'error': 'Clé API invalide'}), 401
        
        return f(noeud, *args, **kwargs)
    
    return decorated

def role_required(required_role):
    """Décorateur pour vérifier le rôle utilisateur"""
    def decorator(f):
        @wraps(f)
        def decorated(payload, *args, **kwargs):
            user_role = payload.get('role')
            
            roles_hierarchy = {'readonly': 1, 'user': 2, 'admin': 3}
            
            if roles_hierarchy.get(user_role, 0) < roles_hierarchy.get(required_role, 0):
                return jsonify({'error': 'Permissions insuffisantes'}), 403
            
            return f(payload, *args, **kwargs)
        return decorated
    return decorator
