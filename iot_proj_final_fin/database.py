import mysql.connector
from mysql.connector import Error, pooling
from config import Config
from contextlib import contextmanager

class Database:
    """Gestionnaire de connexion MySQL avec pool de connexions"""
    
    def __init__(self):
        try:
            self.pool = pooling.MySQLConnectionPool(
                pool_name="iot_pool",
                pool_size=5,
                pool_reset_session=True,
                host=Config.DB_HOST,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                use_unicode=True
            )
            print("✓ Pool de connexions MySQL créé avec succès")
        except Error as e:
            print(f"✗ Erreur de création du pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Context manager pour obtenir une connexion du pool"""
        connection = None
        try:
            connection = self.pool.get_connection()
            yield connection
        except Error as e:
            if connection:
                connection.rollback()
            print(f"Erreur de connexion: {e}")
            raise
        finally:
            if connection and connection.is_connected():
                connection.close()
    
    def execute_query(self, query, params=None, fetch=True):
        """Exécute une requête avec gestion automatique des transactions"""
        with self.get_connection() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(query, params or ())
                
                if query.strip().upper().startswith('SELECT'):
                    result = cursor.fetchall() if fetch else cursor
                    return result
                else:
                    connection.commit()
                    return {
                        'lastrowid': cursor.lastrowid,
                        'rowcount': cursor.rowcount
                    }
            except Error as e:
                connection.rollback()
                print(f"Erreur d'exécution: {e}")
                raise
            finally:
                cursor.close()
    
    def execute_many(self, query, data_list):
        """Exécute une requête pour plusieurs lignes"""
        with self.get_connection() as connection:
            cursor = connection.cursor()
            try:
                cursor.executemany(query, data_list)
                connection.commit()
                return cursor.rowcount
            except Error as e:
                connection.rollback()
                print(f"Erreur d'exécution multiple: {e}")
                raise
            finally:
                cursor.close()

# Instance globale
db = Database()
