import os
import logging
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, g
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from dotenv import load_dotenv
from models import db, Utilisateur, Notification
from config import config

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_LOG_DIR = os.path.join(_BASE_DIR, 'logs')
os.makedirs(_LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_LOG_DIR, 'app.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Migration
migrate = Migrate()


def create_app(config_name='default'):
    """Factory pour créer l'application Flask"""
    app = Flask(__name__)
    
    # Charger la configuration
    app.config.from_object(config[config_name])
    
    # Créer les dossiers nécessaires
    for folder in ['instance', 'logs', app.config['UPLOAD_FOLDER']]:
        os.makedirs(folder, exist_ok=True)
    
    # Initialiser les extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Initialiser Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.connexion'
    login_manager.login_message = 'Veuillez vous connecter pour accéder à cette page.'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        return Utilisateur.query.get(user_id)
    
    # Enregistrer les blueprints
    from routes.auth import auth_bp
    from routes.tickets import tickets_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes.departements import departements_bp
    from routes.utilisateurs import utilisateurs_bp
    from routes.rapports import rapports_bp
    from routes.parametres import parametres_bp
    
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(departements_bp, url_prefix='/departements')
    app.register_blueprint(utilisateurs_bp, url_prefix='/utilisateurs')
    app.register_blueprint(rapports_bp, url_prefix='/rapports')
    app.register_blueprint(parametres_bp, url_prefix='/parametres')
    
    # Route principale
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('tickets.tableau_bord'))
        return redirect(url_for('auth.connexion'))
    
    # Avant chaque requête
    @app.before_request
    def before_request():
        if current_user.is_authenticated:
            current_user.derniere_activite = datetime.utcnow()
            db.session.commit()
            
            # Charger les notifications non lues
            g.notifications_non_lues = Notification.query.filter_by(
                utilisateur_id=current_user.id,
                lue=False
            ).count()
    
    # Contexte global pour les templates
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.now(),
            'app_name': app.config['APP_NAME'],
            'app_version': app.config['APP_VERSION'],
            'notifications_count': getattr(g, 'notifications_non_lues', 0)
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
        from scripts.create_admin import creer_admin
        creer_admin()
    
    @app.cli.command('reset-db')
    def reset_db():
        """Réinitialise complètement la base de données"""
        if input('Voulez-vous vraiment réinitialiser la base de données? (oui/non): ').lower() == 'oui':
            db.drop_all()
            db.create_all()
            from scripts.init_db import initialiser_base_donnees
            initialiser_base_donnees()
            print('Base de données réinitialisée!')
        else:
            print('Opération annulée.')
    
    return app


if __name__ == '__main__':
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    app.run(
        debug=True,
        host=os.getenv('FLASK_HOST', '127.0.0.1'),
        port=int(os.getenv('FLASK_PORT', 5000))
    )
