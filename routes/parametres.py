from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Utilisateur
from werkzeug.utils import secure_filename
import os

parametres_bp = Blueprint('parametres', __name__)


@parametres_bp.route('/profil')
@login_required
def profil():
    """Afficher le profil de l'utilisateur connecté"""
    stats = {
        'tickets_crees': len(current_user.tickets_crees),
        'tickets_assignes': len([t for t in current_user.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'tickets_resolus': len([t for t in current_user.tickets_assignes if t.statut == 'resolu']),
    }
    
    return render_template('parametres/profil.html', stats=stats)


@parametres_bp.route('/profil/modifier', methods=['GET', 'POST'])
@login_required
def modifier_profil():
    """Modifier le profil de l'utilisateur"""
    if request.method == 'POST':
        nom = request.form.get('nom', '').strip()
        prenom = request.form.get('prenom', '').strip()
        telephone = request.form.get('telephone', '').strip()
        
        # Paramètres de notification
        notifications_email = request.form.get('notifications_email') == 'on'
        notifications_push = request.form.get('notifications_push') == 'on'
        
        # Paramètres d'affichage
        theme = request.form.get('theme', 'light')
        langue = request.form.get('langue', 'fr')
        
        if not all([nom, prenom]):
            flash('Le nom et le prénom sont requis.', 'danger')
            return render_template('parametres/modifier_profil.html')
        
        current_user.nom = nom
        current_user.prenom = prenom
        current_user.telephone = telephone if telephone else None
        current_user.notifications_email = notifications_email
        current_user.notifications_push = notifications_push
        current_user.theme = theme
        current_user.langue = langue
        
        try:
            db.session.commit()
            flash('Profil modifié avec succès!', 'success')
            return redirect(url_for('parametres.profil'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur lors de la modification: {str(e)}', 'danger')
    
    return render_template('parametres/modifier_profil.html')


@parametres_bp.route('/securite', methods=['GET', 'POST'])
@login_required
def securite():
    """Modifier le mot de passe"""
    if request.method == 'POST':
        ancien_password = request.form.get('ancien_password', '')
        nouveau_password = request.form.get('nouveau_password', '')
        confirmation_password = request.form.get('confirmation_password', '')
        
        # Validation
        if not current_user.check_password(ancien_password):
            flash('Ancien mot de passe incorrect.', 'danger')
            return render_template('parametres/securite.html')
        
        if len(nouveau_password) < 8:
            flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
            return render_template('parametres/securite.html')
        
        if nouveau_password != confirmation_password:
            flash('Les mots de passe ne correspondent pas.', 'danger')
            return render_template('parametres/securite.html')
        
        current_user.set_password(nouveau_password)
        
        try:
            db.session.commit()
            flash('Mot de passe modifié avec succès!', 'success')
            return redirect(url_for('parametres.profil'))
        except Exception as e:
            db.session.rollback()
            flash(f'Erreur: {str(e)}', 'danger')
    
    return render_template('parametres/securite.html')


@parametres_bp.route('/notifications')
@login_required
def notifications():
    """Gérer les notifications"""
    from models import Notification
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(
        utilisateur_id=current_user.id
    ).order_by(
        Notification.lue.asc(),
        Notification.date_creation.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('parametres/notifications.html', notifications=notifications)


@parametres_bp.route('/notifications/<string:id>/marquer-lue', methods=['POST'])
@login_required
def marquer_notification_lue(id):
    """Marquer une notification comme lue"""
    from models import Notification
    from datetime import datetime
    
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
        flash(f'Erreur: {str(e)}', 'danger')
    
    return redirect(url_for('parametres.notifications'))


@parametres_bp.route('/notifications/marquer-toutes-lues', methods=['POST'])
@login_required
def marquer_toutes_lues():
    """Marquer toutes les notifications comme lues"""
    from models import Notification
    from datetime import datetime
    
    notifications = Notification.query.filter_by(
        utilisateur_id=current_user.id,
        lue=False
    ).all()
    
    for notif in notifications:
        notif.lue = True
        notif.date_lecture = datetime.utcnow()
    
    try:
        db.session.commit()
        flash(f'{len(notifications)} notification(s) marquée(s) comme lue(s).', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur: {str(e)}', 'danger')
    
    return redirect(url_for('parametres.notifications'))
