import os
from datetime import timedelta

class Config:
    """Configuration de base"""
    # Clé secrète
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production-cosmitto-2024')
    
    # Base de données (PostgreSQL obligatoire)
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is not set. A PostgreSQL database is required.")
    
    # Fix common PostgreSQL URI schemes for SQLAlchemy 2+ and psycopg3
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        
    if db_url.startswith('sqlite:///'):
        import os
        basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        if 'instance' in db_url:
            db_path = os.path.join(basedir, 'CosmittoHUB', 'instance', 'cosmitto.db')
            if not os.path.exists(os.path.dirname(db_path)):
                os.makedirs(os.path.dirname(db_path), exist_ok=True)
            db_url = 'sqlite:///' + db_path.replace('\\', '/')
            
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Auto-reload templates without restarting server
    TEMPLATES_AUTO_RELOAD = True
    
    # Upload de fichiers
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', 'static/uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar'}
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=12)
    SESSION_COOKIE_SECURE = False  # True en production avec HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Email (optionnel) - Supporte SMTP, SMTP_SSL et DavMail (Devit)
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'false').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    
    # IMAP (Pour l'intégration Email-to-Ticket)
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    IMAP_USE_SSL = os.getenv('IMAP_USE_SSL', 'true').lower() == 'true'
    IMAP_USERNAME = os.getenv('IMAP_USERNAME', MAIL_USERNAME) # Souvent le même que MAIL_USERNAME
    IMAP_PASSWORD = os.getenv('IMAP_PASSWORD', MAIL_PASSWORD)
    IMAP_POLL_INTERVAL = int(os.getenv('IMAP_POLL_INTERVAL', 60)) # en secondes
    
    # Pagination
    TICKETS_PER_PAGE = 25
    USERS_PER_PAGE = 50
    
    # Sécurité
    PASSWORD_MIN_LENGTH = 8
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 30
    
    # Application
    APP_NAME = 'Cosmicenter'
    APP_VERSION = '2.0.0'
    SUPPORT_EMAIL = 'support@example.com'
    
    # Langues disponibles
    LANGUAGES = {
        'fr': 'Français',
        'en': 'English',
        'ar': 'العربية'
    }
    
    # Fuseaux horaires
    TIMEZONE = 'Africa/Tunis'


class DevelopmentConfig(Config):
    """Configuration de développement"""
    DEBUG = True
    TESTING = False
    SQLALCHEMY_ECHO = False


class ProductionConfig(Config):
    """Configuration de production"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = False  # Set to True when you actually have HTTPS (SSL) configured
    
    # Forcer HTTPS
    PREFERRED_URL_SCHEME = 'http'


class TestingConfig(Config):
    """Configuration de test"""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


# Mapping des configurations
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
