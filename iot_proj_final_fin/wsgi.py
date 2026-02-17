import sys
import os

# Chemin du projet
project_path = '/home/me/projet_iot'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

# Activer l'environnement virtuel
activate_this = os.path.join(project_path, 'venv', 'bin', 'activate_this.py')
if os.path.exists(activate_this):
    with open(activate_this) as file_:
        exec(file_.read(), dict(__file__=activate_this))

# Importer l'application Flask
from app import app as application

if __name__ == "__main__":
    application.run()
