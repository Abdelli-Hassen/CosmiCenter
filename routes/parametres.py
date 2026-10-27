import logging
import re
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, make_response
from flask_login import login_required, current_user, login_user
from models import db, Utilisateur, Notification
from utils.security import safe_color
from utils.uploads import save_upload, remove_upload, UploadError, IMAGE_EXTENSIONS, MAX_IMAGE_BYTES

parametres_bp = Blueprint('parametres', __name__)
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
LANGUES = ('fr', 'en', 'ar')


def _stats():
    return {
        'tickets_crees': len(current_user.tickets_crees),
        'tickets_assignes': len([t for t in current_user.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'tickets_resolus': len([t for t in current_user.tickets_assignes if t.statut == 'resolu']),
    }


def _describe_device(user_agent):
    """Libellé lisible (« Chrome sur Windows ») déduit du User-Agent de la requête."""
    ua = user_agent or ''
    browser = next((name for key, name in (('Edg/', 'Edge'), ('OPR/', 'Opera'), ('Firefox/', 'Firefox'), ('Chrome/', 'Chrome'), ('Safari/', 'Safari')) if key in ua), 'Navigateur')
    system = next((name for key, name in (('Windows', 'Windows'), ('Android', 'Android'), ('iPhone', 'iOS'), ('iPad', 'iOS'), ('Mac OS', 'macOS'), ('Linux', 'Linux')) if key in ua), 'système inconnu')
    return f'{browser} sur {system}'


def _session_info():
    return {
        'appareil': _describe_device(request.headers.get('User-Agent', '')), 
        'ip': request.remote_addr or '—', 
        'depuis': current_user.derniere_connexion, 
    }


@parametres_bp.route('/profil')
@login_required
def profil():
    """Afficher le profil de l'utilisateur connecté"""
    return render_template('parametres/profil.html', stats=_stats())


@parametres_bp.route('/profil/photo/supprimer', methods=['POST'])
@login_required
def supprimer_photo():
    """Retirer la photo de profil (retour aux initiales)"""
    ancienne = current_user.photo_profil
    if ancienne:
        current_user.photo_profil = None
        try:
            db.session.commit()
            remove_upload(ancienne)
            flash('Photo de profil supprimée.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur suppression photo: {e}', exc_info=True)
            flash('Erreur lors de la suppression de la photo.', 'danger')
    return redirect(url_for('parametres.profil'))


@parametres_bp.route('/profil/modifier', methods=['POST'])
@login_required
def modifier_profil():
    """Modifier le profil de l'utilisateur"""
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    email = request.form.get('email', '').strip().lower()
    telephone = request.form.get('telephone', '').strip()
    poste = request.form.get('poste', '').strip()

    anydesk_id = request.form.get('anydesk_id', '').strip()
    anydesk_password = request.form.get('anydesk_password', '').strip()
    teamviewer_id = request.form.get('teamviewer_id', '').strip()
    teamviewer_password = request.form.get('teamviewer_password', '').strip()
    poste_machine = request.form.get('poste_machine', '').strip()

    theme_str = 'dark' if request.form.get('theme_sombre') == 'on' else 'light'
    notifications_email = request.form.get('notifications_email') == 'on'
    couleur = request.form.get('couleur', '').strip()

    if not all([nom, prenom, email]):
        flash("Le nom, le prénom et l'email sont requis.", 'danger')
        return redirect(url_for('parametres.profil'))
    if not EMAIL_RE.match(email) or len(email) > 120:
        flash("L'adresse email est invalide.", 'danger')
        return redirect(url_for('parametres.profil'))
    if len(nom) > 100 or len(prenom) > 100 or len(poste) > 100 or len(telephone) > 20:
        flash('Un des champs dépasse la longueur autorisée.', 'danger')
        return redirect(url_for('parametres.profil'))
    if couleur and couleur != safe_color(couleur, ''):
        flash("La couleur d'accentuation est invalide.", 'danger')
        return redirect(url_for('parametres.profil'))

    existing_user = Utilisateur.query.filter(
        db.func.lower(Utilisateur.email) == email, Utilisateur.id != current_user.id).first()
    if existing_user:
        flash('Cet email est déjà utilisé par un autre compte.', 'danger')
        return redirect(url_for('parametres.profil'))

    # Photo de profil (images uniquement, nom aléatoire)
    old_photo = None
    new_photo = None
    photo = request.files.get('photo_profil')
    if photo and photo.filename:
        try:
            stored, _original, _size = save_upload(photo, 'profiles', IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
            new_photo = f'profiles/{stored}'
            old_photo = current_user.photo_profil
            current_user.photo_profil = new_photo
        except UploadError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('parametres.profil'))

    current_user.nom = nom
    current_user.prenom = prenom
    current_user.email = email
    current_user.telephone = telephone or None
    current_user.poste = poste or None

    current_user.anydesk_id = anydesk_id[:50] or None
    current_user.anydesk_password = anydesk_password[:100] or None
    current_user.teamviewer_id = teamviewer_id[:50] or None
    current_user.teamviewer_password = teamviewer_password[:100] or None
    current_user.poste_machine = poste_machine[:100] or None

    current_user.theme = theme_str
    current_user.notifications_email = notifications_email
    if couleur:
        current_user.couleur = couleur

    try:
        db.session.commit()
        if old_photo and old_photo != new_photo:
            remove_upload(old_photo)
        flash('Profil modifié avec succès!', 'success')

        resp = redirect(url_for('parametres.profil'))
        resp.set_cookie('chub_theme', theme_str, max_age=31536000, path='/', samesite='Lax')
        return resp

    except Exception as e:
        db.session.rollback()
        if new_photo:
            remove_upload(new_photo)
        logger.error(f'Erreur modification profil: {e}', exc_info=True)
        flash('Erreur lors de la modification du profil.', 'danger')
        return redirect(url_for('parametres.profil'))


@parametres_bp.route('/securite', methods=['GET', 'POST'])
@login_required
def securite():
    """Modifier le mot de passe / déconnecter les autres sessions"""
    stats = _stats()

    if request.method == 'POST':
        action = request.form.get('action', 'change_password')

        if action == 'revoke_all_sessions':
            # Incrémente la version de session : tous les autres appareils sont déconnectés
            current_user.revoke_sessions()
            db.session.commit()
            login_user(current_user._get_current_object(), remember=False)
            flash('Toutes les autres sessions ont été déconnectées.', 'success')
            return redirect(url_for('parametres.securite'))

        elif action == 'change_password':
            ancien_password = request.form.get('ancien_password', '')
            nouveau_password = request.form.get('nouveau_password', '')
            confirmation_password = request.form.get('confirmation_password', '')
            min_len = current_app.config.get('PASSWORD_MIN_LENGTH', 8)

            if not current_user.check_password(ancien_password):
                flash('Ancien mot de passe incorrect.', 'danger')
                return render_template('parametres/securite.html', stats=stats, session_info=_session_info())

            if len(nouveau_password) < min_len:
                flash(f'Le nouveau mot de passe doit contenir au moins {min_len} caractères.', 'danger')
                return render_template('parametres/securite.html', stats=stats, session_info=_session_info())

            if nouveau_password != confirmation_password:
                flash('Les mots de passe ne correspondent pas.', 'danger')
                return render_template('parametres/securite.html', stats=stats, session_info=_session_info())

            if nouveau_password == ancien_password:
                flash("Le nouveau mot de passe doit être différent de l'ancien.", 'danger')
                return render_template('parametres/securite.html', stats=stats, session_info=_session_info())

            current_user.set_password(nouveau_password)
            current_user.revoke_sessions()  # déconnecte les autres appareils

            try:
                db.session.commit()
                login_user(current_user._get_current_object(), remember=False)  # reste connecté ici
                flash('Mot de passe modifié avec succès!', 'success')
                return redirect(url_for('parametres.profil'))
            except Exception as e:
                db.session.rollback()
                logger.error(f'Erreur changement mot de passe: {e}', exc_info=True)
                flash('Erreur lors du changement de mot de passe.', 'danger')

    return render_template('parametres/securite.html', stats=stats, session_info=_session_info())


@parametres_bp.route('/notifications')
@login_required
def notifications():
    """Gérer les notifications"""
    page = request.args.get('page', 1, type=int)

    notifications = Notification.query.filter_by(
        utilisateur_id=current_user.id
    ).order_by(
        Notification.lue.asc(),
        Notification.date_creation.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    return render_template('parametres/notifications.html', notifications=notifications, stats=_stats())


@parametres_bp.route('/notifications/<string:id>/marquer-lue', methods=['POST'])
@login_required
def marquer_notification_lue(id):
    """Marquer une notification comme lue"""
    notification = Notification.query.get_or_404(id)

    if notification.utilisateur_id != current_user.id:
        flash('Accès non autorisé.', 'danger')
        return redirect(url_for('parametres.notifications'))

    notification.lue = True
    notification.date_lecture = datetime.utcnow()

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur marquer_notification_lue: {e}', exc_info=True)
        flash('Erreur lors de la mise à jour.', 'danger')

    return redirect(url_for('parametres.notifications'))


@parametres_bp.route('/notifications/marquer-toutes-lues', methods=['POST'])
@login_required
def marquer_toutes_lues():
    """Marquer toutes les notifications comme lues"""
    try:
        count = Notification.query.filter_by(utilisateur_id=current_user.id, lue=False).update(
            {'lue': True, 'date_lecture': datetime.utcnow()})
        db.session.commit()
        flash(f'{count} notification(s) marquée(s) comme lue(s).', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur marquer_toutes_lues: {e}', exc_info=True)
        flash('Erreur lors de la mise à jour.', 'danger')

    return redirect(url_for('parametres.notifications'))
