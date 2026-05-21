"""
Routes d'authentification pour CosmittoDesk
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models import db, Utilisateur
from werkzeug.security import check_password_hash
import logging

# Créer le blueprint
auth_bp = Blueprint('auth', __name__)
logger = logging.getLogger(__name__)


@auth_bp.route('/connexion', methods=['GET', 'POST'])
def connexion():
    """Page de connexion"""
    # Si l'utilisateur est déjà connecté, rediriger vers le tableau de bord
    if current_user.is_authenticated:
        return redirect(url_for('tickets.tableau_bord'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        # Vérifier que les champs sont remplis
        if not email or not password:
            flash('Veuillez remplir tous les champs', 'danger')
            return render_template('auth/connexion.html')
        
        # Rechercher l'utilisateur
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        
        # Vérifier les identifiants
        if utilisateur and utilisateur.check_password(password):
            # Vérifier que le compte est actif
            if not utilisateur.actif:
                flash('Votre compte a été désactivé. Contactez l\'administrateur.', 'danger')
                logger.warning(f'Tentative de connexion d\'un compte désactivé: {email}')
                return render_template('auth/connexion.html')
            
            # Connecter l'utilisateur
            login_user(utilisateur, remember=remember)
            logger.info(f'Connexion réussie: {email}')
            
            # Rediriger vers la page demandée ou le tableau de bord
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('tickets.tableau_bord'))
        else:
            flash('Email ou mot de passe incorrect', 'danger')
            logger.warning(f'Échec de connexion pour: {email}')
    
    return render_template('auth/connexion.html')


@auth_bp.route('/deconnexion')
@login_required
def deconnexion():
    """Déconnexion de l'utilisateur"""
    logger.info(f'Déconnexion: {current_user.email}')
    logout_user()
    flash('Vous avez été déconnecté avec succès', 'success')
    return redirect(url_for('auth.connexion'))


@auth_bp.route('/profil')
@login_required
def profil():
    """Page de profil de l'utilisateur"""
    return render_template('auth/profil.html', utilisateur=current_user)


@auth_bp.route('/mot-de-passe-oublie', methods=['GET', 'POST'])
def mot_de_passe_oublie():
    """Page de réinitialisation de mot de passe"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        
        utilisateur = Utilisateur.query.filter_by(email=email).first()
        if utilisateur:
            # TODO: Implémenter l'envoi d'email de réinitialisation
            flash('Un email de réinitialisation a été envoyé', 'info')
            logger.info(f'Demande de réinitialisation de mot de passe: {email}')
        else:
            # Ne pas révéler si l'email existe ou non (sécurité)
            flash('Si cet email existe, un lien de réinitialisation a été envoyé', 'info')
        
        return redirect(url_for('auth.connexion'))
    
    return render_template('auth/mot_de_passe_oublie.html')
