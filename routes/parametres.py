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


@parametres_bp.route('/profil/modifier', methods=['POST'])
@login_required
def modifier_profil():
    """Modifier le profil de l'utilisateur"""
    nom = request.form.get('nom', '').strip()
    prenom = request.form.get('prenom', '').strip()
    email = request.form.get('email', '').strip()
    telephone = request.form.get('telephone', '').strip()
    poste = request.form.get('poste', '').strip()
    
    anydesk_id = request.form.get('anydesk_id', '').strip()
    anydesk_password = request.form.get('anydesk_password', '').strip()
    teamviewer_id = request.form.get('teamviewer_id', '').strip()
    teamviewer_password = request.form.get('teamviewer_password', '').strip()
    poste_machine = request.form.get('poste_machine', '').strip()
    
    theme_sombre = request.form.get('theme_sombre') == 'on'
    theme_str = 'dark' if theme_sombre else 'light'
    langue = request.form.get('langue', 'fr')
    couleur = request.form.get('couleur', '').strip()
    
    if not all([nom, prenom, email]):
        flash('Le nom, le prénom et l\'email sont requis.', 'danger')
        return redirect(url_for('parametres.profil'))
    
    # Optional: check if email is taken by another user
    from models import Utilisateur
    existing_user = Utilisateur.query.filter(Utilisateur.email == email, Utilisateur.id != current_user.id).first()
    if existing_user:
        flash('Cet email est déjà utilisé par un autre compte.', 'danger')
        return redirect(url_for('parametres.profil'))
        
    # Handle Photo Upload
    if 'photo_profil' in request.files:
        photo = request.files['photo_profil']
        if photo and photo.filename:
            from werkzeug.utils import secure_filename
            import uuid
            
            # Secure filename and add unique ID
            filename = secure_filename(photo.filename)
            unique_filename = f"{uuid.uuid4()}_{filename}"
            
            # Save the file in the dedicated profile pictures folder
            from flask import current_app
            profiles_folder = os.path.join(current_app.config['UPLOéD_FOLDER'], 'profiles')
            os.makedirs(profiles_folder, exist_ok=True)
            upload_path = os.path.join(profiles_folder, unique_filename)
            photo.save(upload_path)
            
            # Update user (stored relative to static/uploads/)
            current_user.photo_profil = f'profiles/{unique_filename}'
    
    current_user.nom = nom
    current_user.prenom = prenom
    current_user.email = email
    current_user.telephone = telephone if telephone else None
    current_user.poste = poste if poste else None
    
    current_user.anydesk_id = anydesk_id if anydesk_id else None
    current_user.anydesk_password = anydesk_password if anydesk_password else None
    current_user.teamviewer_id = teamviewer_id if teamviewer_id else None
    current_user.teamviewer_password = teamviewer_password if teamviewer_password else None
    current_user.poste_machine = poste_machine if poste_machine else None
    
    current_user.theme = theme_str
    current_user.langue = langue
    if couleur:
        current_user.couleur = couleur
    
    try:
        db.session.commit()
        flash('Profil modifié avec succès!', 'success')
        
        from flask import make_response
        resp = redirect(url_for('parametres.profil'))
        resp.set_cookie('chub_theme', theme_str, max_age=31536000, path='/')
        return resp
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la modification: {str(e)}', 'danger')
        return redirect(url_for('parametres.profil'))
    
    # Optional: check if email is taken by another user
    from models import Utilisateur
    existing_user = Utilisateur.query.filter(Utilisateur.email == email, Utilisateur.id != current_user.id).first()
    if existing_user:
        flash('Cet email est déjà utilisé par un autre compte.', 'danger')
        return redirect(url_for('parametres.profil'))
    
    current_user.nom = nom
    current_user.prenom = prenom
    current_user.email = email
    current_user.telephone = telephone if telephone else None
    current_user.poste = poste if poste else None
    
    current_user.anydesk_id = anydesk_id if anydesk_id else None
    current_user.anydesk_password = anydesk_password if anydesk_password else None
    current_user.teamviewer_id = teamviewer_id if teamviewer_id else None
    current_user.teamviewer_password = teamviewer_password if teamviewer_password else None
    current_user.poste_machine = poste_machine if poste_machine else None
    
    current_user.theme = theme_str
    current_user.langue = langue
    if couleur:
        current_user.couleur = couleur
    
    try:
        db.session.commit()
        flash('Profil modifié avec succès!', 'success')
        
        from flask import make_response
        resp = redirect(url_for('parametres.profil'))
        resp.set_cookie('chub_theme', theme_str, max_age=31536000, path='/')
        return resp
        
    except Exception as e:
        db.session.rollback()
        flash(f'Erreur lors de la modification: {str(e)}', 'danger')
        return redirect(url_for('parametres.profil'))




@parametres_bp.route('/securite', methods=['GET', 'POST'])
@login_required
def securite():
    """Modifier le mot de passe"""
    stats = {
        'tickets_crees': len(current_user.tickets_crees),
        'tickets_assignes': len([t for t in current_user.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'tickets_resolus': len([t for t in current_user.tickets_assignes if t.statut == 'resolu']),
    }
    
    if request.method == 'POST':
        action = request.form.get('action', 'change_password')
        
        if action == 'revoke_all_sessions':
            flash('Toutes les autres sessions ont été déconnectées (simulation).', 'success')
            return redirect(url_for('parametres.securite'))
            
        elif action == 'change_password':
            ancien_password = request.form.get('ancien_password', '')
            nouveau_password = request.form.get('nouveau_password', '')
            confirmation_password = request.form.get('confirmation_password', '')
            
            # Validation
            if not current_user.check_password(ancien_password):
                flash('éncien mot de passe incorrect.', 'danger')
                return render_template('parametres/securite.html', stats=stats)
            
            if len(nouveau_password) < 8:
                flash('Le nouveau mot de passe doit contenir au moins 8 caractères.', 'danger')
                return render_template('parametres/securite.html', stats=stats)
            
            if nouveau_password != confirmation_password:
                flash('Les mots de passe ne correspondent pas.', 'danger')
                return render_template('parametres/securite.html', stats=stats)
            
            current_user.set_password(nouveau_password)
            
            try:
                db.session.commit()
                flash('Mot de passe modifié avec succès!', 'success')
                return redirect(url_for('parametres.profil'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur: {str(e)}', 'danger')

    return render_template('parametres/securite.html', stats=stats)



@parametres_bp.route('/notifications')
@login_required
def notifications():
    """Gérer les notifications"""
    from models import Notification
    stats = {
        'tickets_crees': len(current_user.tickets_crees),
        'tickets_assignes': len([t for t in current_user.tickets_assignes if t.statut not in ['resolu', 'ferme']]),
        'tickets_resolus': len([t for t in current_user.tickets_assignes if t.statut == 'resolu']),
    }
    
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    notifications = Notification.query.filter_by(
        utilisateur_id=current_user.id
    ).order_by(
        Notification.lue.asc(),
        Notification.date_creation.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('parametres/notifications.html', notifications=notifications, stats=stats)


@parametres_bp.route('/notifications/<string:id>/marquer-lue', methods=['POST'])
@login_required
def marquer_notification_lue(id):
    """Marquer une notification comme lue"""
    from models import Notification
    from datetime import datetime
    
    notification = Notification.query.get_or_404(id)
    
    if notification.utilisateur_id != current_user.id:
        flash('éccès non autorisé.', 'danger')
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
