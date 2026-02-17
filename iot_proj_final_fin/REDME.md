# Système IoT - Plateforme de Gestion

## Description
Plateforme complète de gestion de capteurs IoT avec API REST, interface web et système d'alertes par email.

## Architecture
- **Backend**: Flask + MySQL
- **Frontend**: HTML/CSS/JavaScript
- **Serveur Web**: Apache + mod_wsgi
- **Base de données**: MySQL 8.0

## Installation

### Prérequis
- Ubuntu 20.04+
- Python 3.8+
- MySQL 8.0+
- Apache 2.4+

### Configuration
1. Cloner le projet
2. Créer l'environnement virtuel: `python3 -m venv venv`
3. Installer les dépendances: `pip install -r requirements.txt`
4. Configurer la base de données (voir schema.sql)
5. Créer le fichier .env avec les variables d'environnement
6. Configurer Apache (voir iot.conf)

## Utilisation

### API Endpoints

#### Authentification
- `POST /api/auth/login` - Connexion
- `GET /api/auth/verify` - Vérifier le token

#### Capteurs
- `GET /api/capteurs` - Liste des capteurs
- `POST /api/capteurs` - Créer un capteur
- `PUT /api/capteurs/{id}` - Modifier un capteur
- `DELETE /api/capteurs/{id}` - Supprimer un capteur

#### Noeuds
- `GET /api/noeuds` - Liste des noeuds
- `POST /api/noeuds` - Créer un noeud
- `PUT /api/noeuds/{id}` - Modifier un noeud

#### Mesures
- `POST /api/mesures` - Envoyer une mesure (API Key requise)
- `GET /api/mesures` - Récupérer les mesures
- `GET /api/mesures/statistiques` - Statistiques

#### Alertes
- `GET /api/alertes` - Liste des alertes
- `POST /api/alertes` - Créer une alerte
- `GET /api/alertes/logs` - Historique des alertes

## Sécurité
- Authentification JWT pour les utilisateurs
- API Key pour les noeuds IoT
- Validation des données
- Protection CSRF
- Logs détaillés

## Maintenance

### Logs
- Apache: `/var/log/apache2/iot_*.log`
- Application: `~/projet_iot/logs/app.log`

### Sauvegarde base de données
```bash
mysqldump -u iot_user -p iot_db > backup_$(date +%Y%m%d).sql
```

### Redémarrer l'application
```bash
sudo systemctl restart apache2
```

## Auteur
DIALLO - Projet IoT 2025
