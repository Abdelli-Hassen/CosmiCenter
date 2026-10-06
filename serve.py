import os
import logging
from waitress import serve
from app import create_app

# Configurer le logging de production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', 'production.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('waitress')

if __name__ == '__main__':
    # Forcer l'environnement de production
    os.environ['FLASK_ENV'] = 'production'
    
    port = int(os.getenv('FLASK_PORT', 8080))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    print(f"=================================================")
    print(f" Cosmicenter - Mode PRODUCTION (Waitress)")
    print(f" Serveur en ecoute sur : http://{host}:{port}")
    print(f" Appuyez sur CTRL+C pour arreter le serveur")
    print(f"=================================================")
    
    app = create_app('production')
    
    # Lancer le serveur Waitress
    serve(app, host=host, port=port, threads=6)
