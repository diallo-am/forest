from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import json

from config import Config
from database import db
from auth import (token_required, api_key_required, role_required, 
                  generate_token, verify_token)
from notifications import email_notifier
from utils.validators import DataValidator
from utils.security import generate_api_key, hash_password, verify_password
from utils.logger import logger, log_to_database

from ia_prediction import fire_model
# Initialisation de l'application
app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={
    r"/api/*": {
        "origins": "*",  # Permet toutes les origines (pour le développement)
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-API-Key"]
    }
})

# Validator instance
validator = DataValidator()

# ==================== ROUTES WEB (INTERFACE) ====================

@app.route('/')
def index():
    """Page d'accueil"""
    return render_template('index.html')

@app.route('/utilisateurs')
def utilisateurs_page():
    """Page de gestion des utilisateurs"""
    return render_template('utilisateurs.html')

@app.route('/dashboard')
def dashboard():
    """Tableau de bord principal"""
    return render_template('dashboard.html')

@app.route('/capteurs')
def capteurs_page():
    """Page de gestion des capteurs"""
    return render_template('capteurs.html')

@app.route('/noeuds')
def noeuds_page():
    """Page de gestion des noeuds"""
    return render_template('noeuds.html')

@app.route('/alertes')
def alertes_page():
    """Page de gestion des alertes"""
    return render_template('alertes.html')

# ==================== AUTHENTIFICATION ====================

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Connexion utilisateur"""
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'error': 'Username et password requis'}), 400
        
        # Récupérer l'utilisateur
        query = """
            SELECT id, username, email, password_hash, role, actif 
            FROM utilisateurs 
            WHERE username = %s
        """
        result = db.execute_query(query, (username,))
        
        if not result:
            log_to_database('warning', 'login_failed', f'User not found: {username}')
            return jsonify({'error': 'Identifiants invalides'}), 401
        
        user = result[0]
        
        if not user['actif']:
            return jsonify({'error': 'Compte désactivé'}), 403
        
        # Vérifier le mot de passe
        if not verify_password(password, user['password_hash']):
            log_to_database('warning', 'login_failed', f'Wrong password for: {username}')
            return jsonify({'error': 'Identifiants invalides'}), 401
        
        # Générer le token
        token = generate_token(user['id'], user['username'], user['role'])
        
        # Mettre à jour la dernière connexion
        update_query = "UPDATE utilisateurs SET derniere_connexion = NOW() WHERE id = %s"
        db.execute_query(update_query, (user['id'],))
        
        log_to_database('info', 'login_success', f'User logged in: {username}')
        
        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'role': user['role']
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Erreur login: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/auth/verify', methods=['GET'])
@token_required
def verify_auth(payload):
    """Vérifie un token"""
    return jsonify({'valid': True, 'user': payload}), 200

@app.route('/api/auth/register', methods=['POST'])
@token_required
@role_required('admin')
def register(payload):
    """Créer un nouvel utilisateur (admin seulement)"""
    try:
        data = request.get_json()
        
        username = validator.sanitize_string(data.get('username'), 50)
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not all([username, email, password]):
            return jsonify({'error': 'Données incomplètes'}), 400
        
        if role not in ['admin', 'user', 'readonly']:
            return jsonify({'error': 'Rôle invalide'}), 400
        
        # Vérifier si l'utilisateur existe
        check_query = "SELECT id FROM utilisateurs WHERE username = %s OR email = %s"
        existing = db.execute_query(check_query, (username, email))
        
        if existing:
            return jsonify({'error': 'Utilisateur déjà existant'}), 409
        
        # Hash du mot de passe
        password_hash = hash_password(password)
        
        # Générer un token API
        api_token = generate_api_key('user')
        
        # Insérer l'utilisateur
        insert_query = """
            INSERT INTO utilisateurs (username, email, password_hash, role, api_token)
            VALUES (%s, %s, %s, %s, %s)
        """
        result = db.execute_query(insert_query, (username, email, password_hash, role, api_token))
        
        log_to_database('info', 'user_created', f'New user: {username}')
        
        return jsonify({
            'message': 'Utilisateur créé',
            'user_id': result['lastrowid'],
            'api_token': api_token
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur register: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== API UTILISATEURS (GESTION) ====================

@app.route('/api/utilisateurs', methods=['GET'])
@token_required
@role_required('admin')
def get_utilisateurs(payload):
    """Récupérer tous les utilisateurs (admin seulement)"""
    try:
        query = """
            SELECT id, username, email, role, actif, date_creation, derniere_connexion
            FROM utilisateurs
            ORDER BY date_creation DESC
        """
        utilisateurs = db.execute_query(query)
        return jsonify(utilisateurs), 200
        
    except Exception as e:
        logger.error(f"Erreur get_utilisateurs: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/utilisateurs/<int:id>', methods=['PUT'])
@token_required
@role_required('admin')
def update_utilisateur(payload, id):
    """Mettre à jour un utilisateur (activation/désactivation)"""
    try:
        data = request.get_json()
        actif = data.get('actif')
        
        if actif is None:
            return jsonify({'error': 'Statut actif requis'}), 400
        
        query = "UPDATE utilisateurs SET actif = %s WHERE id = %s"
        result = db.execute_query(query, (actif, id))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        log_to_database('info', 'user_updated', f'Utilisateur {id} {"activé" if actif else "désactivé"}')
        
        return jsonify({'message': 'Utilisateur mis à jour'}), 200
        
    except Exception as e:
        logger.error(f"Erreur update_utilisateur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/utilisateurs/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_utilisateur(payload, id):
    """Supprimer un utilisateur (admin seulement)"""
    try:
        query = "DELETE FROM utilisateurs WHERE id = %s"
        result = db.execute_query(query, (id,))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
        log_to_database('warning', 'user_deleted', f'Utilisateur {id} supprimé par {payload["username"]}')
        
        return jsonify({'message': 'Utilisateur supprimé'}), 200
        
    except Exception as e:
        logger.error(f"Erreur delete_utilisateur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== API CAPTEURS ====================

@app.route('/api/capteurs', methods=['GET'])
@token_required
def get_capteurs(payload):
    """Récupérer tous les capteurs"""
    try:
        actif = request.args.get('actif')
        type_capteur = request.args.get('type')
        
        query = "SELECT * FROM capteurs WHERE 1=1"
        params = []
        
        if actif is not None:
            query += " AND actif = %s"
            params.append(actif == 'true')
        
        if type_capteur:
            query += " AND type = %s"
            params.append(type_capteur)
        
        query += " ORDER BY nom"
        
        capteurs = db.execute_query(query, tuple(params) if params else None)
        return jsonify(capteurs), 200
        
    except Exception as e:
        logger.error(f"Erreur get_capteurs: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/capteurs/<int:id>', methods=['GET'])
@token_required
def get_capteur(payload, id):
    """Récupérer un capteur spécifique"""
    try:
        query = "SELECT * FROM capteurs WHERE id = %s"
        result = db.execute_query(query, (id,))
        
        if not result:
            return jsonify({'error': 'Capteur non trouvé'}), 404
        
        return jsonify(result[0]), 200
        
    except Exception as e:
        logger.error(f"Erreur get_capteur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/capteurs', methods=['POST'])
@token_required
@role_required('user')
def add_capteur(payload):
    """Ajouter un nouveau capteur"""
    try:
        data = request.get_json()
        
        nom = validator.sanitize_string(data.get('nom'), 100)
        type_capteur = validator.sanitize_string(data.get('type'), 50)
        unite = validator.sanitize_string(data.get('unite'), 20)
        description = validator.sanitize_string(data.get('description'), 500)
        
        if not nom or not type_capteur:
            return jsonify({'error': 'Nom et type requis'}), 400
        
        query = """
            INSERT INTO capteurs (nom, type, unite, description)
            VALUES (%s, %s, %s, %s)
        """
        result = db.execute_query(query, (nom, type_capteur, unite, description))
        
        log_to_database('info', 'capteur_created', f'Capteur créé: {nom}')
        
        return jsonify({
            'message': 'Capteur ajouté',
            'id': result['lastrowid']
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur add_capteur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/capteurs/<int:id>', methods=['PUT'])
@token_required
@role_required('user')
def update_capteur(payload, id):
    """Mettre à jour un capteur"""
    try:
        data = request.get_json()
        
        nom = validator.sanitize_string(data.get('nom'), 100)
        type_capteur = validator.sanitize_string(data.get('type'), 50)
        unite = validator.sanitize_string(data.get('unite'), 20)
        description = validator.sanitize_string(data.get('description'), 500)
        actif = data.get('actif', True)
        
        query = """
            UPDATE capteurs 
            SET nom = %s, type = %s, unite = %s, description = %s, actif = %s
            WHERE id = %s
        """
        result = db.execute_query(query, (nom, type_capteur, unite, description, actif, id))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Capteur non trouvé'}), 404
        
        log_to_database('info', 'capteur_updated', f'Capteur mis à jour: {id}')
        
        return jsonify({'message': 'Capteur mis à jour'}), 200
        
    except Exception as e:
        logger.error(f"Erreur update_capteur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/capteurs/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_capteur(payload, id):
    """Supprimer un capteur"""
    try:
        query = "DELETE FROM capteurs WHERE id = %s"
        result = db.execute_query(query, (id,))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Capteur non trouvé'}), 404
        
        log_to_database('warning', 'capteur_deleted', f'Capteur supprimé: {id}')
        
        return jsonify({'message': 'Capteur supprimé'}), 200
        
    except Exception as e:
        logger.error(f"Erreur delete_capteur: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== API NOEUDS ====================

@app.route('/api/noeuds', methods=['GET'])
@token_required
def get_noeuds(payload):
    """Récupérer tous les noeuds"""
    try:
        statut = request.args.get('statut')
        
        query = "SELECT * FROM noeuds WHERE 1=1"
        params = []
        
        if statut:
            query += " AND statut = %s"
            params.append(statut)
        
        query += " ORDER BY nom"
        
        noeuds = db.execute_query(query, tuple(params) if params else None)
        
        # Masquer les clés API complètes
        for noeud in noeuds:
            if 'api_key' in noeud:
                noeud['api_key'] = noeud['api_key'][:10] + '...'
        
        return jsonify(noeuds), 200
        
    except Exception as e:
        logger.error(f"Erreur get_noeuds: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds/<int:id>', methods=['GET'])
@token_required
def get_noeud(payload, id):
    """Récupérer un noeud spécifique"""
    try:
        query = """
            SELECT n.*, 
                   GROUP_CONCAT(c.nom SEPARATOR ', ') as capteurs
            FROM noeuds n
            LEFT JOIN noeud_capteur nc ON n.id = nc.noeud_id
            LEFT JOIN capteurs c ON nc.capteur_id = c.id
            WHERE n.id = %s
            GROUP BY n.id
        """
        result = db.execute_query(query, (id,))
        
        if not result:
            return jsonify({'error': 'Noeud non trouvé'}), 404
        
        noeud = result[0]
        # Masquer la clé API
        noeud['api_key'] = noeud['api_key'][:10] + '...'
        
        return jsonify(noeud), 200
        
    except Exception as e:
        logger.error(f"Erreur get_noeud: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds', methods=['POST'])
@token_required
@role_required('user')
def add_noeud(payload):
    """Ajouter un nouveau noeud"""
    try:
        data = request.get_json()
        
        nom = validator.sanitize_string(data.get('nom'), 100)
        adresse_mac = data.get('adresse_mac', '').upper()
        adresse_ip = data.get('adresse_ip')
        localisation = validator.sanitize_string(data.get('localisation'), 200)
        modele = validator.sanitize_string(data.get('modele'), 100)
        
        # Validation
        if not nom or not adresse_mac:
            return jsonify({'error': 'Nom et adresse MAC requis'}), 400
        
        if not validator.validate_mac_address(adresse_mac):
            return jsonify({'error': 'Adresse MAC invalide'}), 400
        
        if adresse_ip and not validator.validate_ip_address(adresse_ip):
            return jsonify({'error': 'Adresse IP invalide'}), 400
        
        # Générer une clé API unique
        api_key = generate_api_key('noeud_api_key')
        
        query = """
            INSERT INTO noeuds (nom, adresse_mac, adresse_ip, localisation, modele, api_key)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        result = db.execute_query(query, (nom, adresse_mac, adresse_ip, localisation, modele, api_key))
        
        log_to_database('info', 'noeud_created', f'Noeud créé: {nom}')
        
        return jsonify({
            'message': 'Noeud ajouté',
            'id': result['lastrowid'],
            'api_key': api_key  # Retourner la clé complète une seule fois
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur add_noeud: {e}")
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'Adresse MAC déjà existante'}), 409
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds/<int:id>', methods=['PUT'])
@token_required
@role_required('user')
def update_noeud(payload, id):
    """Mettre à jour un noeud"""
    try:
        data = request.get_json()
        
        nom = validator.sanitize_string(data.get('nom'), 100)
        adresse_ip = data.get('adresse_ip')
        localisation = validator.sanitize_string(data.get('localisation'), 200)
        modele = validator.sanitize_string(data.get('modele'), 100)
        firmware_version = validator.sanitize_string(data.get('firmware_version'), 50)
        statut = data.get('statut')
        
        if adresse_ip and not validator.validate_ip_address(adresse_ip):
            return jsonify({'error': 'Adresse IP invalide'}), 400
        
        if statut and statut not in ['actif', 'inactif', 'maintenance', 'erreur']:
            return jsonify({'error': 'Statut invalide'}), 400
        
        query = """
            UPDATE noeuds 
            SET nom = %s, adresse_ip = %s, localisation = %s, 
                modele = %s, firmware_version = %s, statut = %s
            WHERE id = %s
        """
        result = db.execute_query(query, (nom, adresse_ip, localisation, modele, 
                                         firmware_version, statut, id))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Noeud non trouvé'}), 404
        
        log_to_database('info', 'noeud_updated', f'Noeud mis à jour: {id}')
        
        return jsonify({'message': 'Noeud mis à jour'}), 200
        
    except Exception as e:
        logger.error(f"Erreur update_noeud: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_noeud(payload, id):
    """Supprimer un noeud"""
    try:
        query = "DELETE FROM noeuds WHERE id = %s"
        result = db.execute_query(query, (id,))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Noeud non trouvé'}), 404
        
        log_to_database('warning', 'noeud_deleted', f'Noeud supprimé: {id}')
        
        return jsonify({'message': 'Noeud supprimé'}), 200
        
    except Exception as e:
        logger.error(f"Erreur delete_noeud: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds/<int:noeud_id>/capteurs/<int:capteur_id>', methods=['POST'])
@token_required
@role_required('user')
def associer_capteur_noeud(payload, noeud_id, capteur_id):
    """Associer un capteur à un noeud"""
    try:
        query = """
            INSERT INTO noeud_capteur (noeud_id, capteur_id)
            VALUES (%s, %s)
        """
        db.execute_query(query, (noeud_id, capteur_id))
        
        log_to_database('info', 'capteur_associated', 
                       f'Capteur {capteur_id} associé au noeud {noeud_id}')
        
        return jsonify({'message': 'Association créée'}), 201
        
    except Exception as e:
        logger.error(f"Erreur association: {e}")
        if 'Duplicate entry' in str(e):
            return jsonify({'error': 'Association déjà existante'}), 409
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/noeuds/<int:noeud_id>/capteurs/<int:capteur_id>', methods=['DELETE'])
@token_required
@role_required('user')
def dissocier_capteur_noeud(payload, noeud_id, capteur_id):
    """Dissocier un capteur d'un noeud"""
    try:
        query = """
            DELETE FROM noeud_capteur
            WHERE noeud_id = %s AND capteur_id = %s
        """
        result = db.execute_query(query, (noeud_id, capteur_id))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Association non trouvée'}), 404
        
        log_to_database('info', 'capteur_dissociated', 
                       f'Capteur {capteur_id} dissocié du noeud {noeud_id}')
        
        return jsonify({'message': 'Dissociation effectuée'}), 200
        
    except Exception as e:
        logger.error(f"Erreur dissociation: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== API MESURES (RÉCEPTION DES DONNÉES) ====================

@app.route('/api/mesures', methods=['POST'])
@api_key_required
def add_mesure(noeud):
    """Recevoir et enregistrer une mesure (protégé par API key)"""
    try:
        data = request.get_json()
        
        capteur_id = data.get('capteur_id')
        valeur = data.get('valeur')
        timestamp = data.get('timestamp')
        metadata = data.get('metadata')
        
        if not capteur_id or valeur is None:
            return jsonify({'error': 'capteur_id et valeur requis'}), 400
        
        # Validation de la valeur
        if not validator.validate_sensor_value(valeur, -100, 10000):
            return jsonify({'error': 'Valeur hors limites'}), 400
        
        # Vérifier que le capteur est associé au noeud
        check_query = """
            SELECT 1 FROM noeud_capteur 
            WHERE noeud_id = %s AND capteur_id = %s
        """
        association = db.execute_query(check_query, (noeud['id'], capteur_id))
        
        if not association:
            return jsonify({'error': 'Capteur non associé à ce noeud'}), 403
        
        # Insérer la mesure
        insert_query = """
            INSERT INTO mesures (noeud_id, capteur_id, valeur, timestamp, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        ts = timestamp if timestamp else datetime.now()
        meta_json = json.dumps(metadata) if metadata else None
        
        result = db.execute_query(insert_query, (noeud['id'], capteur_id, valeur, ts, meta_json))
        mesure_id = result['lastrowid']
        
        # Vérifier les alertes
        check_alerts(capteur_id, noeud['id'], valeur, mesure_id)
        
        return jsonify({
            'message': 'Mesure enregistrée',
            'id': mesure_id
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur add_mesure: {e}")
        log_to_database('error', 'mesure_failed', str(e), noeud['id'])
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/mesures/bulk', methods=['POST'])
@api_key_required
def add_mesures_bulk(noeud):
    """Recevoir plusieurs mesures en une fois"""
    try:
        data = request.get_json()
        mesures = data.get('mesures', [])
        
        if not mesures or not isinstance(mesures, list):
            return jsonify({'error': 'Format invalide'}), 400
        
        if len(mesures) > 100:
            return jsonify({'error': 'Maximum 100 mesures par requête'}), 400
        
        inserted_count = 0
        errors = []
        
        for idx, mesure in enumerate(mesures):
            try:
                capteur_id = mesure.get('capteur_id')
                valeur = mesure.get('valeur')
                timestamp = mesure.get('timestamp', datetime.now())
                
                if not capteur_id or valeur is None:
                    errors.append({'index': idx, 'error': 'Données manquantes'})
                    continue
                
                # Vérifier l'association
                check_query = """
                    SELECT 1 FROM noeud_capteur 
                    WHERE noeud_id = %s AND capteur_id = %s
                """
                if not db.execute_query(check_query, (noeud['id'], capteur_id)):
                    errors.append({'index': idx, 'error': 'Capteur non associé'})
                    continue
                
                # Insérer
                insert_query = """
                    INSERT INTO mesures (noeud_id, capteur_id, valeur, timestamp)
                    VALUES (%s, %s, %s, %s)
                """
                result = db.execute_query(insert_query, (noeud['id'], capteur_id, valeur, timestamp))
                
                # Vérifier les alertes
                check_alerts(capteur_id, noeud['id'], valeur, result['lastrowid'])
                
                inserted_count += 1
                
            except Exception as e:
                errors.append({'index': idx, 'error': str(e)})
        
        return jsonify({
            'message': f'{inserted_count} mesures enregistrées',
            'inserted': inserted_count,
            'errors': errors if errors else None
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur add_mesures_bulk: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


# ==================== API LECTURE DES DONNÉES ====================

@app.route('/api/mesures', methods=['GET'])
@token_required
def get_mesures(payload):
    """Récupérer les mesures avec filtres"""
    try:
        capteur_id = request.args.get('capteur_id')
        noeud_id = request.args.get('noeud_id')
        limit = request.args.get('limit', 100)
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        
        query = """
            SELECT m.*, c.nom as capteur_nom, c.type, c.unite,
                   n.nom as noeud_nom, n.localisation
            FROM mesures m
            JOIN capteurs c ON m.capteur_id = c.id
            JOIN noeuds n ON m.noeud_id = n.id
            WHERE 1=1
        """
        params = []
        
        if capteur_id:
            query += " AND m.capteur_id = %s"
            params.append(capteur_id)
        
        if noeud_id:
            query += " AND m.noeud_id = %s"
            params.append(noeud_id)
        
        if date_debut:
            query += " AND m.timestamp >= %s"
            params.append(date_debut)
        
        if date_fin:
            query += " AND m.timestamp <= %s"
            params.append(date_fin)
        
        query += " ORDER BY m.timestamp DESC LIMIT %s"
        params.append(int(limit))
        
        mesures = db.execute_query(query, tuple(params))
        
        return jsonify(mesures), 200
        
    except Exception as e:
        logger.error(f"Erreur get_mesures: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/mesures/derniere/<int:capteur_id>', methods=['GET'])
@token_required
def get_derniere_mesure(payload, capteur_id):
    """Récupérer la dernière mesure d'un capteur"""
    try:
        noeud_id = request.args.get('noeud_id')
        
        query = """
            SELECT m.*, c.nom as capteur_nom, c.type, c.unite,
                   n.nom as noeud_nom
            FROM mesures m
            JOIN capteurs c ON m.capteur_id = c.id
            JOIN noeuds n ON m.noeud_id = n.id
            WHERE m.capteur_id = %s
        """
        params = [capteur_id]
        
        if noeud_id:
            query += " AND m.noeud_id = %s"
            params.append(noeud_id)
        
        query += " ORDER BY m.timestamp DESC LIMIT 1"
        
        result = db.execute_query(query, tuple(params))
        
        if not result:
            return jsonify({'error': 'Aucune mesure trouvée'}), 404
        
        return jsonify(result[0]), 200
        
    except Exception as e:
        logger.error(f"Erreur get_derniere_mesure: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/mesures/statistiques', methods=['GET'])
@token_required
def get_statistiques_mesures(payload):
    """Statistiques des mesures"""
    try:
        capteur_id = request.args.get('capteur_id')
        noeud_id = request.args.get('noeud_id')
        date_debut = request.args.get('date_debut')
        date_fin = request.args.get('date_fin')
        
        query = """
            SELECT 
                c.nom as capteur_nom,
                c.type,
                c.unite,
                COUNT(*) as total_mesures,
                AVG(m.valeur) as moyenne,
                MIN(m.valeur) as minimum,
                MAX(m.valeur) as maximum,
                STDDEV(m.valeur) as ecart_type,
                MIN(m.timestamp) as premiere_mesure,
                MAX(m.timestamp) as derniere_mesure
            FROM mesures m
            JOIN capteurs c ON m.capteur_id = c.id
            WHERE 1=1
        """
        params = []
        
        if capteur_id:
            query += " AND m.capteur_id = %s"
            params.append(capteur_id)
        
        if noeud_id:
            query += " AND m.noeud_id = %s"
            params.append(noeud_id)
        
        if date_debut:
            query += " AND m.timestamp >= %s"
            params.append(date_debut)
        
        if date_fin:
            query += " AND m.timestamp <= %s"
            params.append(date_fin)
        
        query += " GROUP BY c.id, c.nom, c.type, c.unite"
        
        stats = db.execute_query(query, tuple(params) if params else None)
        
        return jsonify(stats), 200
        
    except Exception as e:
        logger.error(f"Erreur get_statistiques_mesures: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/mesures/historique', methods=['GET'])
@token_required
def get_historique(payload):
    """Historique des mesures avec agrégation temporelle"""
    try:
        capteur_id = request.args.get('capteur_id', type=int)
        intervalle = request.args.get('intervalle', 'heure')  # heure, jour, semaine
        limit = request.args.get('limit', 24, type=int)
        
        if not capteur_id:
            return jsonify({'error': 'capteur_id requis'}), 400
        
        # Déterminer le format de date selon l'intervalle
        format_map = {
            'heure': '%Y-%m-%d %H:00:00',
            'jour': '%Y-%m-%d',
            'semaine': '%Y-%u'
        }
        
        date_format = format_map.get(intervalle, '%Y-%m-%d %H:00:00')
        
        query = f"""
            SELECT 
                DATE_FORMAT(timestamp, '{date_format}') as periode,
                AVG(valeur) as moyenne,
                MIN(valeur) as minimum,
                MAX(valeur) as maximum,
                COUNT(*) as nombre_mesures
            FROM mesures
            WHERE capteur_id = %s
            GROUP BY periode
            ORDER BY periode DESC
            LIMIT %s
        """
        
        historique = db.execute_query(query, (capteur_id, limit))
        
        return jsonify(historique), 200
        
    except Exception as e:
        logger.error(f"Erreur get_historique: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== API ALERTES ====================
@app.route('/api/alertes/<int:id>', methods=['GET'])
@token_required
def get_alerte(payload, id):
    """Récupérer une alerte spécifique"""
    try:
        query = """
            SELECT a.*, c.nom as capteur_nom, c.type, n.nom as noeud_nom
            FROM alertes a
            JOIN capteurs c ON a.capteur_id = c.id
            LEFT JOIN noeuds n ON a.noeud_id = n.id
            WHERE a.id = %s
        """
        result = db.execute_query(query, (id,))
        
        if not result:
            return jsonify({'error': 'Alerte non trouvée'}), 404
        
        return jsonify(result[0]), 200
        
    except Exception as e:
        logger.error(f"Erreur get_alerte: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


@app.route('/api/alertes', methods=['GET'])
@token_required
def get_alertes(payload):
    """Récupérer toutes les alertes"""
    try:
        actif = request.args.get('actif')
        severite = request.args.get('severite')
        
        query = """
            SELECT a.*, c.nom as capteur_nom, c.type, n.nom as noeud_nom
            FROM alertes a
            JOIN capteurs c ON a.capteur_id = c.id
            LEFT JOIN noeuds n ON a.noeud_id = n.id
            WHERE 1=1
        """
        params = []
        
        if actif is not None:
            query += " AND a.actif = %s"
            params.append(actif == 'true')
        
        if severite:
            query += " AND a.severite = %s"
            params.append(severite)
        
        query += " ORDER BY a.severite DESC, a.date_creation DESC"
        
        alertes = db.execute_query(query, tuple(params) if params else None)
        
        return jsonify(alertes), 200
        
    except Exception as e:
        logger.error(f"Erreur get_alertes: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/alertes', methods=['POST'])
@token_required
@role_required('user')
def add_alerte(payload):
    """Créer une nouvelle alerte"""
    try:
        data = request.get_json()
        
        capteur_id = data.get('capteur_id')
        noeud_id = data.get('noeud_id')
        type_alerte = data.get('type_alerte')
        severite = data.get('severite')
        seuil_min = data.get('seuil_min')
        seuil_max = data.get('seuil_max')
        message = validator.sanitize_string(data.get('message'), 500)
        email_notification = data.get('email_notification', True)
        
        # Validation
        if not capteur_id or not type_alerte or not severite:
            return jsonify({'error': 'Données incomplètes'}), 400
        
        if type_alerte not in ['seuil_min', 'seuil_max', 'anomalie', 'hors_ligne', 'autre']:
            return jsonify({'error': 'Type alerte invalide'}), 400
        
        if severite not in ['info', 'warning', 'critical']:
            return jsonify({'error': 'Sévérité invalide'}), 400
        
        query = """
            INSERT INTO alertes (capteur_id, noeud_id, type_alerte, severite, 
                               seuil_min, seuil_max, message, email_notification)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        result = db.execute_query(query, (capteur_id, noeud_id, type_alerte, severite,
                                         seuil_min, seuil_max, message, email_notification))
        
        log_to_database('info', 'alerte_created', f'Alerte créée pour capteur {capteur_id}')
        
        return jsonify({
            'message': 'Alerte créée',
            'id': result['lastrowid']
        }), 201
        
    except Exception as e:
        logger.error(f"Erreur add_alerte: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/alertes/<int:id>', methods=['PUT'])
@token_required
@role_required('user')
def update_alerte(payload, id):
    """Mettre à jour une alerte"""
    try:
        data = request.get_json()
        
        type_alerte = data.get('type_alerte')
        severite = data.get('severite')
        seuil_min = data.get('seuil_min')
        seuil_max = data.get('seuil_max')
        message = data.get('message')
        email_notification = data.get('email_notification')
        actif = data.get('actif')
        capteur_id = data.get('capteur_id')
        noeud_id = data.get('noeud_id')
        
        # Validation
        if type_alerte and type_alerte not in ['seuil_min', 'seuil_max', 'anomalie', 'hors_ligne', 'autre']:
            return jsonify({'error': 'Type alerte invalide'}), 400
        
        if severite and severite not in ['info', 'warning', 'critical']:
            return jsonify({'error': 'Sévérité invalide'}), 400
        
        query = """
            UPDATE alertes 
            SET capteur_id = %s,
                noeud_id = %s,
                type_alerte = %s, 
                severite = %s, 
                seuil_min = %s, 
                seuil_max = %s, 
                message = %s, 
                email_notification = %s, 
                actif = %s
            WHERE id = %s
        """
        result = db.execute_query(query, (
            capteur_id,
            noeud_id,
            type_alerte, 
            severite, 
            seuil_min, 
            seuil_max,
            message, 
            email_notification, 
            actif, 
            id
        ))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Alerte non trouvée'}), 404
        
        log_to_database('info', 'alerte_updated', f'Alerte mise à jour: {id}')
        
        return jsonify({'message': 'Alerte mise à jour'}), 200
        
    except Exception as e:
        logger.error(f"Erreur update_alerte: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/alertes/<int:id>', methods=['DELETE'])
@token_required
@role_required('admin')
def delete_alerte(payload, id):
    """Supprimer une alerte"""
    try:
        query = "DELETE FROM alertes WHERE id = %s"
        result = db.execute_query(query, (id,))
        
        if result['rowcount'] == 0:
            return jsonify({'error': 'Alerte non trouvée'}), 404
        
        log_to_database('warning', 'alerte_deleted', f'Alerte supprimée: {id}')
        
        return jsonify({'message': 'Alerte supprimée'}), 200
        
    except Exception as e:
        logger.error(f"Erreur delete_alerte: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/alertes/logs', methods=['GET'])
@token_required
def get_logs_alertes(payload):
    """Récupérer l'historique des alertes déclenchées"""
    try:
        alerte_id = request.args.get('alerte_id')
        limit = request.args.get('limit', 100)
        
        query = """
            SELECT la.*, a.type_alerte, a.severite, a.message as alerte_message,
                   c.nom as capteur_nom, n.nom as noeud_nom
            FROM logs_alertes la
            JOIN alertes a ON la.alerte_id = a.id
            JOIN capteurs c ON a.capteur_id = c.id
            LEFT JOIN noeuds n ON a.noeud_id = n.id
            WHERE email_envoye = 1
        """
        params = []
        
        if alerte_id:
            query += " AND la.alerte_id = %s"
            params.append(alerte_id)
        
        query += " ORDER BY la.timestamp DESC LIMIT %s"
        params.append(int(limit))
        
        logs = db.execute_query(query, tuple(params))
        
        return jsonify(logs), 200
        
    except Exception as e:
        logger.error(f"Erreur get_logs_alertes: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


# ==================== FONCTION VÉRIFICATION ALERTES ====================
def check_alerts(capteur_id, noeud_id, valeur, mesure_id):
    """Vérifie les alertes avec IA (3 capteurs)"""
    try:
        # CORRECTION : Utiliser 'co2' au lieu de 'fumee'
        query_mesures = """
            SELECT c.type, m.valeur 
            FROM mesures m
            JOIN capteurs c ON m.capteur_id = c.id
            WHERE m.noeud_id = %s 
            AND c.type IN ('temperature', 'humidite', 'co2')
            AND m.id = (
                SELECT MAX(m2.id) 
                FROM mesures m2 
                JOIN capteurs c2 ON m2.capteur_id = c2.id
                WHERE m2.noeud_id = %s AND c2.type = c.type
            )
        """
        mesures_recentes = db.execute_query(query_mesures, (noeud_id, noeud_id))
        
        temperature = None
        humidity = None
        smoke = None
        
        for mesure in mesures_recentes:
            if mesure['type'] == 'temperature':
                temperature = mesure['valeur']
            elif mesure['type'] == 'humidite':
                humidity = mesure['valeur']
            elif mesure['type'] == 'co2':  # CORRECTION ICI
                smoke = mesure['valeur']
        
        logger.info(f"Noeud {noeud_id}: T={temperature}, H={humidity}, Fumee={smoke}")
        
        if temperature is not None and humidity is not None and smoke is not None:
            prediction = fire_model.predict_fire_risk(
                temperature=temperature,
                humidity=humidity,
                smoke_level=smoke
            )
            
            logger.info(f"Prediction IA Noeud {noeud_id}: {prediction}")
            
            if prediction['status'] in ['WARNING', 'CRITICAL']:
                query_alerte = """
                    SELECT id, email_notification FROM alertes 
                    WHERE noeud_id = %s 
                    AND type_alerte = 'anomalie'
                    AND actif = TRUE
                    LIMIT 1
                """
                alerte_existante = db.execute_query(query_alerte, (noeud_id,))
                
                if alerte_existante:
                    alerte_id = alerte_existante[0]['id']
                    
                    message = f"IA: {prediction['status']} - Risque: {prediction['fire_risk_percent']:.1f}% | T={temperature}°C, H={humidity}%, Fumee={prediction['smoke_level']:.0f}ppm"
                    
                    log_query = """
                        INSERT INTO logs_alertes (alerte_id, mesure_id, valeur_mesuree, message)
                        VALUES (%s, %s, %s, %s)
                    """
                    result = db.execute_query(log_query, (alerte_id, mesure_id, prediction['fire_risk_percent'], message))
                    
                    if alerte_existante[0]['email_notification']:
                        email_notifier.send_alert_notification(
                            alerte_id,
                            result['lastrowid'],
                            prediction['fire_risk_percent'],
                            message
                        )
                    logger.warning(f"Alerte IA declenchee noeud {noeud_id}")
                else:
                    logger.warning(f"Prediction {prediction['status']} mais aucune alerte 'anomalie' configuree pour noeud {noeud_id}")
        
        query = """
            SELECT * FROM alertes 
            WHERE capteur_id = %s 
            AND actif = TRUE
            AND (noeud_id = %s OR noeud_id IS NULL)
        """
        alertes = db.execute_query(query, (capteur_id, noeud_id))
        
        for alerte in alertes:
            triggered = False
            message = None
            
            if alerte['type_alerte'] == 'seuil_min' and alerte['seuil_min']:
                if valeur < alerte['seuil_min']:
                    triggered = True
                    message = f"Valeur {valeur} inferieure au seuil minimum {alerte['seuil_min']}"
            
            elif alerte['type_alerte'] == 'seuil_max' and alerte['seuil_max']:
                if valeur > alerte['seuil_max']:
                    triggered = True
                    message = f"Valeur {valeur} superieure au seuil maximum {alerte['seuil_max']}"
            
            if triggered:
                log_query = """
                    INSERT INTO logs_alertes (alerte_id, mesure_id, valeur_mesuree, message)
                    VALUES (%s, %s, %s, %s)
                """
                result = db.execute_query(log_query, (alerte['id'], mesure_id, valeur, message))
                log_alerte_id = result['lastrowid']
                
                if alerte['email_notification']:
                    email_notifier.send_alert_notification(
                        alerte['id'], 
                        log_alerte_id, 
                        valeur, 
                        message
                    )
                
                logger.warning(f"Alerte declenchee: {alerte['id']} - {message}")
        
    except Exception as e:
        logger.error(f"Erreur check_alerts: {e}")
# ==================== API LOGS SYSTÈME ====================

@app.route('/api/logs', methods=['GET'])
@token_required
@role_required('admin')
def get_logs(payload):
    """Récupérer les logs système"""
    try:
        niveau = request.args.get('niveau')
        noeud_id = request.args.get('noeud_id')
        limit = request.args.get('limit', 200)
        
        query = """
            SELECT l.*, n.nom as noeud_nom
            FROM logs l
            LEFT JOIN noeuds n ON l.noeud_id = n.id
            WHERE 1=1
        """
        params = []
        
        if niveau:
            query += " AND l.niveau = %s"
            params.append(niveau)
        
        if noeud_id:
            query += " AND l.noeud_id = %s"
            params.append(noeud_id)
        
        query += " ORDER BY l.timestamp DESC LIMIT %s"
        params.append(int(limit))
        
        logs = db.execute_query(query, tuple(params))
        
        return jsonify(logs), 200
        
    except Exception as e:
        logger.error(f"Erreur get_logs: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500


#====================Endpoint pour prediction manuelle==============

@app.route('/api/ia/predict', methods=['POST'])
@token_required
def predict_fire_risk_api(payload):
    """Endpoint pour prédiction IA manuelle"""
    try:
        data = request.get_json()
        
        temperature = data.get('temperature')
        humidity = data.get('humidity')
        raw_gas = data.get('raw_gas')
        smoke_level = data.get('smoke_level')
        
        if temperature is None or humidity is None:
            return jsonify({'error': 'temperature et humidity requis'}), 400
        
        prediction = fire_model.predict_fire_risk(
            temperature=float(temperature),
            humidity=float(humidity),
            raw_gas=int(raw_gas) if raw_gas else None,
            smoke_level=float(smoke_level) if smoke_level else None
        )
        
        return jsonify(prediction), 200
        
    except Exception as e:
        logger.error(f"Erreur prédiction API: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

@app.route('/api/ia/status', methods=['GET'])
@token_required
def ia_status(payload):
    """Vérifier si le modèle IA est chargé"""
    return jsonify({
        'model_loaded': fire_model.model is not None,
        'model_path': fire_model.model_path
    }), 200

# ==================== DASHBOARD / STATISTIQUES ====================

@app.route('/api/dashboard/summary', methods=['GET'])
@token_required
def get_dashboard_summary(payload):
    """Résumé pour le dashboard"""
    try:
        # Nombre total de capteurs actifs
        capteurs_query = "SELECT COUNT(*) as total FROM capteurs WHERE actif = TRUE"
        capteurs_count = db.execute_query(capteurs_query)[0]['total']
        
        # Nombre total de noeuds actifs
        noeuds_query = "SELECT COUNT(*) as total FROM noeuds WHERE statut = 'actif'"
        noeuds_count = db.execute_query(noeuds_query)[0]['total']
        
        # Nombre total de mesures
        mesures_query = "SELECT COUNT(*) as total FROM mesures"
        mesures_count = db.execute_query(mesures_query)[0]['total']
        
        # Mesures des dernières 24h
        mesures_24h_query = """
            SELECT COUNT(*) as total 
            FROM mesures 
            WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        """
        mesures_24h = db.execute_query(mesures_24h_query)[0]['total']
        
        # Alertes actives
        alertes_query = "SELECT COUNT(*) as total FROM alertes WHERE actif = TRUE"
        alertes_count = db.execute_query(alertes_query)[0]['total']
        
        # Alertes déclenchées aujourd'hui
        alertes_today_query = """
            SELECT COUNT(*) as total 
            FROM logs_alertes 
            WHERE DATE(timestamp) = CURDATE()
        """
        alertes_today = db.execute_query(alertes_today_query)[0]['total']
        
        # Dernières mesures par capteur
        dernieres_mesures_query = """
            SELECT c.nom as capteur, c.type, c.unite,
                   m.valeur, m.timestamp, n.nom as noeud
            FROM capteurs c
            JOIN mesures m ON c.id = m.capteur_id
            JOIN noeuds n ON m.noeud_id = n.id
            WHERE m.id IN (
                SELECT MAX(id) FROM mesures GROUP BY capteur_id
            )
            LIMIT 10
        """
        dernieres_mesures = db.execute_query(dernieres_mesures_query)
        
        summary = {
            'capteurs_actifs': capteurs_count,
            'noeuds_actifs': noeuds_count,
            'total_mesures': mesures_count,
            'mesures_24h': mesures_24h,
            'alertes_actives': alertes_count,
            'alertes_aujourd_hui': alertes_today,
            'dernieres_mesures': dernieres_mesures
        }
        
        return jsonify(summary), 200
        
    except Exception as e:
        logger.error(f"Erreur get_dashboard_summary: {e}")
        return jsonify({'error': 'Erreur serveur'}), 500

# ==================== GESTION DES ERREURS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Route non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erreur 500: {error}")
    return jsonify({'error': 'Erreur interne du serveur'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Exception non gérée: {e}")
    return jsonify({'error': 'Une erreur est survenue'}), 500

# ==================== LANCEMENT ====================

if __name__ == '__main__':
    logger.info("Démarrage de l'application IoT")
    app.run(host='0.0.0.0', port=5000, debug=Config.DEBUG)
