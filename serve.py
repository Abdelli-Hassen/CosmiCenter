import os
import socket
import logging
from waitress import serve
from app import create_app
from utils.console_keys import start_restart_listener

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

def local_ips():
    """Adresses IPv4 de ce poste ; la première est celle de la connexion réseau active."""
    ips = []
    try:
        # Aucun paquet n'est envoyé : on demande seulement quelle interface serait utilisée
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('10.255.255.255', 1))
            ips.append(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            if ip not in ips and not ip.startswith(('127.', '169.254.')):
                ips.append(ip)
    except OSError:
        pass
    return [ip for ip in ips if not ip.startswith('127.')]


if __name__ == '__main__':
    # Forcer l'environnement de production
    os.environ['FLASK_ENV'] = 'production'
    
    port = int(os.getenv('FLASK_PORT', 8080))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    print(f"=================================================")
    print(f" CosmiCenter - Mode PRODUCTION (Waitress)")
    print(f" Serveur en ecoute sur : http://{host}:{port}")
    ips = local_ips()
    if host.startswith('127.') or host == 'localhost':
        print(f" Local uniquement : les autres appareils (telephone...) ne pourront PAS se connecter.")
        print(f" Pour le partage reseau : FLASK_HOST=0.0.0.0 dans .env, puis relancer.")
    elif not ips:
        print(f" Aucune adresse reseau detectee : connectez ce poste a un Wi-Fi / reseau, puis relancez.")
    else:
        # Calculé à chaque démarrage : suit le Wi-Fi / le réseau sur lequel ce poste est connecté
        print(f" A ouvrir depuis un autre appareil (meme Wi-Fi / reseau) :")
        for i, ip in enumerate(ips):
            print(f"   http://{ip}:{port}" + ("   <-- principale (celle du reseau actif)" if i == 0 else ""))
    can_restart = start_restart_listener()
    if can_restart:
        print(f" Appuyez sur R pour redemarrer le serveur")
    print(f" Appuyez sur CTRL+C pour arreter le serveur")
    print(f"=================================================")
    
    app = create_app('production')
    
    # Lancer le serveur Waitress
    serve(app, host=host, port=port, threads=6)
