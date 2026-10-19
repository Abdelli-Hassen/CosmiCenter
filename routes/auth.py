"""
Routes d'authentification pour CosmiCenter
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Utilisateur
from datetime import datetime, timedelta
from utils.security import is_safe_redirect, rotate_csrf_token
import logging

# Créer le blueprint
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


def _lock_remaining(utilisateur):
    """Minutes restantes avant fin du verrouillage temporaire (0 si le compte n'est pas/plus verrouillé)."""
    if not utilisateur.verrouille:
        return 0
    duration = timedelta(minutes=current_app.config['LOCKOUT_DURATION_MINUTES'])
    since = utilisateur.date_verrouillage
    if since is None:
        # Verrouillage hérité (avant l'introduction de la durée) : seul un administrateur peut le lever.
        return -1
    remaining = since + duration - datetime.utcnow()
    if remaining.total_seconds() <= 0:
        return 0
    return int(remaining.total_seconds() // 60) + 1


@auth_bp.route('/connexion', methods=['GET', 'POST'])
def connexion():
    """Page de connexion"""
    # Si l'utilisateur est déjà connecté, rediriger vers le tableau de bord
    if current_user.is_authenticated:
        return redirect(url_for('tickets.tableau_bord'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') in ('on', '1', 'true', 'True')
        max_attempts = current_app.config['MAX_LOGIN_ATTEMPTS']

        # Vérifier que les champs sont remplis
        if not email or not password:
            flash('Veuillez remplir tous les champs', 'danger')
            return render_template('auth/connexion.html')

        # Rechercher l'utilisateur (email insensible à la casse)
        utilisateur = Utilisateur.query.filter(db.func.lower(Utilisateur.email) == email).first()

        if utilisateur is None:
            flash('Email ou mot de passe incorrect', 'danger')
            logger.warning('Échec de connexion (utilisateur introuvable)')
            return render_template('auth/connexion.html')

        # Verrouillage temporaire : levé automatiquement après LOCKOUT_DURATION_MINUTES
        remaining = _lock_remaining(utilisateur)
        if utilisateur.verrouille and remaining == 0:
            utilisateur.verrouille = False
            utilisateur.date_verrouillage = None
            utilisateur.tentatives_connexion = 0
            db.session.commit()
        elif utilisateur.verrouille:
            if remaining > 0:
                flash(f"Compte temporairement verrouillé après {max_attempts} tentatives infructueuses. "
                      f"Réessayez dans {remaining} minute(s) ou contactez un administrateur.", "danger")
            else:
                flash("Votre compte est verrouillé. Veuillez contacter un administrateur.", "danger")
            logger.warning(f"Tentative de connexion sur un compte verrouillé: id={utilisateur.id}")
            return render_template('auth/connexion.html')

        if utilisateur.check_password(password):
            if not utilisateur.actif:
                flash("Votre compte a été désactivé. Contactez l'administrateur.", "danger")
                logger.warning(f"Tentative de connexion d'un compte désactivé: id={utilisateur.id}")
                return render_template('auth/connexion.html')

            utilisateur.tentatives_connexion = 0
            utilisateur.derniere_connexion = datetime.utcnow()
            db.session.commit()

            rotate_csrf_token()  # nouveau jeton CSRF après authentification
            login_user(utilisateur, remember=remember)
            logger.info(f"Connexion réussie: id={utilisateur.id}")

            # Redirection uniquement vers un chemin local (pas d'open redirect)
            next_page = request.args.get('next')
            if is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for('tickets.tableau_bord'))

        # Mauvais mot de passe
        utilisateur.tentatives_connexion = (utilisateur.tentatives_connexion or 0) + 1
        if utilisateur.tentatives_connexion >= max_attempts:
            utilisateur.verrouille = True
            utilisateur.date_verrouillage = datetime.utcnow()
            logger.warning(f"Compte verrouillé suite à de multiples échecs: id={utilisateur.id}")
            flash(f"Trop de tentatives : compte verrouillé pendant "
                  f"{current_app.config['LOCKOUT_DURATION_MINUTES']} minutes.", 'danger')
        else:
            flash('Email ou mot de passe incorrect', 'danger')
        db.session.commit()
        logger.warning(f'Échec de connexion pour: id={utilisateur.id}')

    return render_template('auth/connexion.html')


@auth_bp.route('/deconnexion', methods=['POST'])
@login_required
def deconnexion():
    """Déconnexion de l'utilisateur (POST + CSRF : empêche la déconnexion forcée par un lien tiers)"""
    logger.info(f'Déconnexion: id={current_user.id}')
    logout_user()
    flash('Vous avez été déconnecté avec succès', 'success')
    return redirect(url_for('auth.connexion'))


@auth_bp.route('/profil')
@login_required
def profil():
    """Page de profil de l'utilisateur"""
    return render_template('auth/profil.html', utilisateur=current_user)


@auth_bp.route('/mot-de-passe-oublie', methods=['GET'])
def mot_de_passe_oublie():
    """Page d'aide : la réinitialisation est effectuée par un administrateur"""
    return render_template('auth/mot_de_passe_oublie.html')
