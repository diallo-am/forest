#!/usr/bin/env python3
import bcrypt
import mysql.connector

# Configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'iot_user',
    'password': 'iot1234567890!',
    'database': 'iot_db'
}

def create_admin():
    # Hash du mot de passe "admin"
    password = "admin"
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Connexion à la base
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Supprimer l'admin existant si présent
        cursor.execute("DELETE FROM utilisateurs WHERE username = 'admin'")
        
        # Créer le nouvel admin
        query = """
            INSERT INTO utilisateurs (username, email, password_hash, role, api_token, actif)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        cursor.execute(query, (
            'admin',
            'admin@iot.local',
            password_hash,
            'admin',
            'admin_token_' + bcrypt.gensalt().decode('utf-8')[:20],
            True
        ))
        
        conn.commit()
        print("✓ Utilisateur admin créé avec succès")
        print(f"  Username: admin")
        print(f"  Password: admin")
        print(f"  Email: admin@iot.local")
        
    except Exception as e:
        print(f"✗ Erreur: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_admin()
