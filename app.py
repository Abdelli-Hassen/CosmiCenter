import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv(override=True)

from flask import Flask, render_template, redirect, url_for, request
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from models import db, Utilisateur, Notification
from config import config, validate_config
from utils.security import init_csrf, init_security_headers, is_loopback
from utils.schema import ensure_schema

# Configuration du logging (rotation : 5 Mo x 5 fichiers)
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_LOG_DIR = os.path.join(_BASE_DIR, 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(os.path.join(_LOG_DIR, 'app.log'), maxBytes=5 * 1024 * 1024,
                            backupCount=5, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# Migration
migrate = Migrate()

# Fréquence maximale d'écriture de « dernière activité » par utilisateur
ACTIVITY_WRITE_INTERVAL = timedelta(seconds=60)


def create_app(config_name='default'):
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)

    # Charger la configuration
    app.config.from_object(config[config_name])

    # Le débogueur Werkzeug permet d'exécuter du code : jamais sur une interface exposée au réseau.
    bind_host = os.getenv('FLASK_HOST', '127.0.0.1')
    if app.debug and not is_loopback(bind_host):
        app.debug = False
        logger.warning("Mode debug désactivé : FLASK_HOST=%s expose le serveur au réseau.", bind_host)

    validate_config(app)

    # Reverse proxy (Nginx) : récupère l'adresse IP du visiteur, le schéma https et l'hôte d'origine
    if app.config.get('BEHIND_PROXY'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Créer les dossiers nécessaires
    for folder in [os.path.join(_BASE_DIR, 'instance'), _LOG_DIR, app.config['UPLOAD_FOLDER']]:
        os.makedirs(folder, exist_ok=True)

    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        db.create_all()
        ensure_schema(db)
        from services.referentiels import ensure_defaults
        ensure_defaults()

    # Sécurité : CSRF, en-têtes, accès aux uploads
    init_csrf(app)
    init_security_headers(app)

    # Initialiser Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.connexion'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        # Identifiant de session = "<id>:<session_version>" (voir Utilisateur.get_id)
        if not user_id or ':' not in user_id:
            return None
        uid, _, version = user_id.partition(':')
        user = db.session.get(Utilisateur, uid)
        if user is None or not user.actif:
            return None
        try:
            if int(version) != (user.session_version or 0):
                return None
        except ValueError:
            return None
        return user

    # Enregistrer les blueprints
    from routes.auth import auth_bp
    from routes.tickets import tickets_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes.departements import departements_bp
    from routes.utilisateurs import utilisateurs_bp
    from routes.rapports import rapports_bp
    from routes.parametres import parametres_bp
    from routes.chat import chat_bp
    from routes.base_connaissance import base_connaissance_bp
    from routes.pdv import pdv_bp
    from routes.companies import companies_bp
    from routes.suggestions import suggestions_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(departements_bp, url_prefix='/departements')
    app.register_blueprint(utilisateurs_bp, url_prefix='/utilisateurs')
    app.register_blueprint(rapports_bp, url_prefix='/rapports')
    app.register_blueprint(parametres_bp, url_prefix='/parametres')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(base_connaissance_bp, url_prefix='/base_connaissance')
    app.register_blueprint(pdv_bp, url_prefix='/pdv')
    app.register_blueprint(companies_bp, url_prefix='/companies')
    app.register_blueprint(suggestions_bp, url_prefix='/suggestions')

    # Polling IMAP (email -> ticket) : uniquement si IMAP_ENABLE_POLLING=true
    if app.config.get('IMAP_ENABLE_POLLING') and not app.testing:
        # Avec le reloader Werkzeug, ne démarrer que dans le processus enfant
        if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            from services.email_service import start_imap_polling
            start_imap_polling(app)

    # Route principale
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('tickets.tableau_bord'))
        return redirect(url_for('auth.connexion'))

    # Favicon
    @app.route('/favicon.ico')
    def favicon():
        from flask import send_from_directory
        return send_from_directory(os.path.join(app.root_path, 'static', 'images'),
                                   'logo-icon.png', mimetype='image/png')

    # Avant chaque requête : dernière activité (écriture limitée à 1/minute/utilisateur)
    @app.before_request
    def before_request():
        if request.endpoint == 'static' or not current_user.is_authenticated:
            return
        now = datetime.utcnow()
        last = current_user.derniere_activite
        if last is None or now - last > ACTIVITY_WRITE_INTERVAL:
            try:
                current_user.derniere_activite = now
                db.session.commit()
            except Exception:
                db.session.rollback()

    # Contexte global pour les templates
    @app.context_processor
    def inject_globals():
        if current_user.is_authenticated:
            user_notifications = Notification.query.filter_by(utilisateur_id=current_user.id).order_by(Notification.date_creation.desc()).limit(20).all()
            notifications_non_lues = sum(1 for n in user_notifications if not n.lue)
            ticket_notifs_count = sum(1 for n in user_notifications if not n.lue and getattr(n, 'type_notification', '') == 'ticket')
            from utils.permissions import unopened_tickets_count, unread_messages_count
            tickets_non_ouverts = unopened_tickets_count(current_user)
            messages_non_lus = unread_messages_count(current_user)
        else:
            user_notifications = []
            notifications_non_lues = 0
            ticket_notifs_count = 0
            tickets_non_ouverts = 0
            messages_non_lus = 0

        return {
            'now': datetime.now(),
            'app_name': app.config['APP_NAME'],
            'app_version': app.config['APP_VERSION'],
            'support_email': app.config['SUPPORT_EMAIL'],
            'notifications_count': notifications_non_lues,
            'ticket_notifs_count': ticket_notifs_count,
            'tickets_non_ouverts': tickets_non_ouverts,
            'messages_non_lus': messages_non_lus,
            'notifications': user_notifications
        }

    # Filtres Jinja personnalisés
    @app.template_filter('datetime_format')
    def datetime_format(value, format='%d/%m/%Y %H:%M'):
        if value is None:
            return ''
        return value.strftime(format)

    @app.template_filter('humanize_datetime')
    def humanize_datetime(value):
        if value is None:
            return ''

        now = datetime.utcnow()
        diff = now - value

        if diff.days > 365:
            return f"il y a {diff.days // 365} an(s)"
        elif diff.days > 30:
            return f"il y a {diff.days // 30} mois"
        elif diff.days > 0:
            return f"il y a {diff.days} jour(s)"
        elif diff.seconds > 3600:
            return f"il y a {diff.seconds // 3600} heure(s)"
        elif diff.seconds > 60:
            return f"il y a {diff.seconds // 60} minute(s)"
        else:
            return "à l'instant"

    @app.template_filter('file_size')
    def file_size(bytes):
        if bytes is None:
            return '0 B'

        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes < 1024.0:
                return f"{bytes:.1f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.1f} TB"

    # Gestionnaires d'erreurs
    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html'), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return redirect(url_for('auth.connexion'))

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f'Erreur serveur: {error}', exc_info=True)
        return render_template('errors/500.html'), 500

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return render_template('errors/413.html'), 413

    # Commandes CLI personnalisées
    @app.cli.command('init-db')
    def init_db():
        """Initialise la base de données avec des données de base"""
        from scripts.init_db import initialiser_base_donnees
        initialiser_base_donnees()
        print('Base de données initialisée avec succès!')

    @app.cli.command('create-admin')
    def create_admin():
        """Crée un utilisateur administrateur"""
        from scripts.init_db import creer_admin
        creer_admin()

    @app.cli.command('reset-db')
    def reset_db():
        """Réinitialise complètement la base de données"""
        if input('Voulez-vous vraiment réinitialiser la base de données? (oui/non): ').lower() == 'oui':
            db.drop_all()
            db.create_all()
            ensure_schema(db)
            from scripts.init_db import initialiser_base_donnees
            initialiser_base_donnees()
            print('Base de données réinitialisée!')
        else:
            print('Opération annulée.')

    return app


if __name__ == '__main__':
    env = os.getenv('FLASK_ENV', 'development')
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    app = create_app(env)
    # app.debug a déjà été forcé à False si l'hôte n'est pas une adresse locale (voir create_app)
    is_dev = app.debug
    if not is_loopback(host):
        logger.info("Serveur partagé sur le réseau : http://<ip-de-ce-poste>:%s (débogueur désactivé)",
                    os.getenv('FLASK_PORT', 8080))
    app.run(
        debug=is_dev,
        host=host,
        port=int(os.getenv('FLASK_PORT', 8080)),
        use_reloader=is_dev,
        threaded=True
    )
