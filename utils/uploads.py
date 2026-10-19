"""Enregistrement sécurisé des fichiers uploadés."""
import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024   # 10 Mo par fichier (affiché dans le formulaire)
MAX_IMAGE_BYTES = 5 * 1024 * 1024         # 5 Mo pour photos / logos


class UploadError(ValueError):
    """Fichier refusé (extension, taille ou nom invalide)."""


def uploads_root():
    return current_app.config['UPLOAD_FOLDER']


def save_upload(file_storage, subdir, allowed_extensions, max_bytes, keep_original_ext=True):
    """
    Enregistre `file_storage` dans <UPLOAD_FOLDER>/<subdir> sous un nom aléatoire.
    Retourne (nom_stocké, nom_original, taille). Lève UploadError si refusé.
    """
    original = secure_filename(file_storage.filename or '')
    if not original or '.' not in original:
        raise UploadError(f"Nom de fichier invalide : « {file_storage.filename} ».")
    ext = original.rsplit('.', 1)[1].lower()
    if ext not in allowed_extensions:
        raise UploadError(f"Type de fichier non autorisé : .{ext}")

    target_dir = os.path.join(uploads_root(), subdir) if subdir else uploads_root()
    os.makedirs(target_dir, exist_ok=True)
    stored = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join(target_dir, stored)
    file_storage.save(path)

    size = os.path.getsize(path)
    if size > max_bytes:
        os.remove(path)
        raise UploadError(f"« {original} » dépasse la taille maximale de {max_bytes // (1024 * 1024)} Mo.")
    if size == 0:
        os.remove(path)
        raise UploadError(f"« {original} » est vide.")
    return stored, original, size


def remove_upload(relative_path):
    """Supprime un fichier uploadé (chemin relatif à UPLOAD_FOLDER), sans sortir du dossier."""
    if not relative_path:
        return
    root = os.path.abspath(uploads_root())
    full = os.path.abspath(os.path.join(root, relative_path))
    if full.startswith(root + os.sep) and os.path.isfile(full):
        try:
            os.remove(full)
        except OSError:
            pass
