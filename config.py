import os
from datetime import timedelta

_BASE_DIR = os.path.abspath(os.path.dirname(__file__))
_DEFAULT_SECRET = 'dev-secret-key-change-in-production-cosmitto-2024'


def _env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def _normalize_db_url(url):
    """Normalise l'URL PostgreSQL pour SQLAlchemy 2 + psycopg3."""
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql://', 1)
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url


class Config:
    """Configuration de base"""
    # Clé secrète (obligatoire hors développement, voir validate_config)
    SECRET_KEY = os.getenv('SECRET_KEY', _DEFAULT_SECRET)

    # Base de données (PostgreSQL obligatoire)
    _db_url = os.getenv('DATABASE_URL')
    if not _db_url:
        raise ValueError("DATABASE_URL environment variable is not set. A PostgreSQL database is required.")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(_db_url)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}

    # Auto-reload templates without restarting server
    TEMPLATES_AUTO_RELOAD = True

    # Upload de fichiers (chemin absolu, indépendant du dossier de lancement)
    _upload = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    UPLOAD_FOLDER = _upload if os.path.isabs(_upload) else os.path.join(_BASE_DIR, _upload)
    MAX_CONTENT_LENGTH = 150 * 1024 * 1024  # 150 Mo par requête (30 Mo par fichier, voir utils/uploads.py)
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'log', 'csv', 'zip', 'rar'}

    # Session / cookies. SESSION_COOKIE_SECURE=true uniquement derrière HTTPS.
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = 'Lax'
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    CSRF_ENABLED = True

    # Derrière un reverse proxy (Nginx) : fait confiance aux en-têtes X-Forwarded-* (adresse IP réelle, HTTPS, nom d'hôte).
    # À activer UNIQUEMENT si l'application n'est joignable que via le proxy (FLASK_HOST=127.0.0.1).
    BEHIND_PROXY = _env_bool('BEHIND_PROXY', False)

    # URL publique (liens dans les emails). Ex: http://192.168.1.20:8080 ; sinon l'hôte de la requête est utilisé.
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')

    # Email (optionnel) - SMTP / SMTP_SSL
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    MAIL_TIMEOUT = int(os.getenv('MAIL_TIMEOUT', 20))

    # Pagination
    TICKETS_PER_PAGE = 25
    USERS_PER_PAGE = 50

    # Sécurité des comptes
    PASSWORD_MIN_LENGTH = 8
    MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', 7))
    LOCKOUT_DURATION_MINUTES = int(os.getenv('LOCKOUT_DURATION_MINUTES', 30))

    # Application
    APP_NAME = 'CosmiCenter'
    APP_VERSION = '2.7.2'
    SUPPORT_EMAIL = os.getenv('SUPPORT_EMAIL', 'support@example.com')

    # Langues disponibles
    LANGUAGES = {
        'fr': 'Français',
        'en': 'English',
        'ar': 'العربية'
    }

    # Fuseaux horaires
    TIMEZONE = 'Africa/Tunis'


class DevelopmentConfig(Config):
    """Configuration de développement (le débogueur n'est activé qu'en boucle locale, voir app.py)"""
    DEBUG = _env_bool('FLASK_DEBUG', False)
    TESTING = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG = False
    TESTING = False
    TEMPLATES_AUTO_RELOAD = False


class TestingConfig(Config):
    """Configuration de test"""
    TESTING = True
    CSRF_ENABLED = False


def validate_config(app):
    """Refuse de démarrer en production avec la clé secrète par défaut."""
    if app.config['SECRET_KEY'] == _DEFAULT_SECRET and not app.debug and not app.testing:
        raise RuntimeError(
            "SECRET_KEY n'est pas défini (valeur par défaut détectée). "
            "Définissez une clé aléatoire dans .env avant de démarrer en production."
        )


# Mapping des configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
