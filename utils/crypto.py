"""Chiffrement transparent des champs sensibles (ex. mots de passe AnyDesk / TeamViewer)."""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy.types import Text, TypeDecorator

PREFIX = 'enc::'


def _fernet():
    secret = os.getenv('FIELD_ENCRYPTION_KEY')
    if not secret:
        try:
            secret = current_app.config['SECRET_KEY']
        except RuntimeError:  # hors contexte applicatif
            secret = os.getenv('SECRET_KEY', '')
    key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode('utf-8')).digest())
    return Fernet(key)


def encrypt_value(value):
    if value is None or value == '' or str(value).startswith(PREFIX):
        return value
    return PREFIX + _fernet().encrypt(str(value).encode('utf-8')).decode('ascii')


def decrypt_value(value):
    if value is None or not str(value).startswith(PREFIX):
        return value  # valeur historique en clair : lue telle quelle, chiffrée à la prochaine écriture
    try:
        return _fernet().decrypt(str(value)[len(PREFIX):].encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        return None


class EncryptedString(TypeDecorator):
    """Colonne texte chiffrée au repos (Fernet, clé dérivée de FIELD_ENCRYPTION_KEY ou SECRET_KEY)."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_value(value)

    def process_result_value(self, value, dialect):
        return decrypt_value(value)
