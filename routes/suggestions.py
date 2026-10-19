from html import escape

from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from models import db, Suggestion, Utilisateur, Role
from utils.permissions import role_level

suggestions_bp = Blueprint('suggestions', __name__)

TYPES_SUGGESTION = ['bug', 'amelioration', 'nouvelle_fonctionnalite']
STATUTS_SUGGESTION = ['nouveau', 'lu', 'accepte', 'refuse', 'en_cours', 'termine']


def _is_suggestion_admin():
    """Administrateurs (niveau >= 90) ou rôles nommés Administrateur / Super Administrateur."""
    role = current_user.role
    return bool(role and (role.nom in ('Administrateur', 'Super Administrateur') or role_level(current_user) >= 90))


@suggestions_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        titre = (request.form.get('titre') or '').strip()
        description = (request.form.get('description') or '').strip()
        type_suggestion = request.form.get('type_suggestion', 'amelioration')
        if type_suggestion not in TYPES_SUGGESTION:
            type_suggestion = 'amelioration'

        if not titre or not description:
            flash("Veuillez remplir tous les champs obligatoires.", "danger")
            return redirect(url_for('suggestions.index'))
        if len(titre) > 200:
            flash("Le titre est trop long (200 caractères maximum).", "danger")
            return redirect(url_for('suggestions.index'))

        db.session.add(Suggestion(
            titre=titre,
            description=description,
            type_suggestion=type_suggestion,
            auteur_id=current_user.id
        ))
        db.session.commit()

        # Email aux administrateurs (contenu échappé : il provient d'un utilisateur)
        from services.email_service import send_email_notification
        admins = Utilisateur.query.join(Role, Utilisateur.role_id == Role.id).filter(
            Role.niveau >= 90, Utilisateur.actif.is_(True)).all()
        admin_emails = [a.email for a in admins if a.email]
        if admin_emails:
            base = current_app.config.get('PUBLIC_BASE_URL') or request.host_url.rstrip('/')
            contenu_html = f"""
            <div style="font-family: Arial, sans-serif; padding: 20px;">
                <h2>Nouvelle boîte à idées !</h2>
                <p><strong>De :</strong> {escape(current_user.prenom)} {escape(current_user.nom)}</p>
                <p><strong>Type :</strong> {escape(type_suggestion.replace('_', ' ').title())}</p>
                <div style="background: #f4f4f5; padding: 15px; border-left: 4px solid #3b82f6; margin: 20px 0;">
                    {escape(description).replace(chr(10), '<br>')}
                </div>
                <p><a href="{escape(base)}{url_for('suggestions.index')}" style="padding: 10px 15px; background: #3b82f6; color: white; text-decoration: none; border-radius: 5px;">Voir les suggestions</a></p>
            </div>
            """
            send_email_notification(current_app._get_current_object(),
                                    f"💡 Nouvelle suggestion : {titre}", admin_emails, contenu_html)

        flash("Merci ! Votre suggestion a été envoyée avec succès.", "success")
        return redirect(url_for('suggestions.index'))

    # GET : toutes les suggestions pour un administrateur, sinon uniquement les siennes
    if _is_suggestion_admin():
        mes_suggestions = Suggestion.query.order_by(Suggestion.date_creation.desc()).all()
    else:
        mes_suggestions = Suggestion.query.filter_by(auteur_id=current_user.id).order_by(Suggestion.date_creation.desc()).all()

    return render_template('suggestions/index.html', suggestions=mes_suggestions)


@suggestions_bp.route('/<suggestion_id>/statut', methods=['POST'])
@login_required
def modifier_statut(suggestion_id):
    if not _is_suggestion_admin():
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('suggestions.index'))

    suggestion = Suggestion.query.get_or_404(suggestion_id)
    nouveau_statut = request.form.get('statut')
    if nouveau_statut not in STATUTS_SUGGESTION:
        flash("Statut invalide.", "danger")
        return redirect(url_for('suggestions.index'))

    suggestion.statut = nouveau_statut
    db.session.commit()
    flash("Statut mis à jour avec succès.", "success")
    return redirect(url_for('suggestions.index'))


@suggestions_bp.route('/<suggestion_id>/supprimer', methods=['POST'])
@login_required
def supprimer(suggestion_id):
    if not _is_suggestion_admin():
        flash("Accès non autorisé.", "danger")
        return redirect(url_for('suggestions.index'))

    suggestion = Suggestion.query.get_or_404(suggestion_id)
    db.session.delete(suggestion)
    db.session.commit()

    flash("Suggestion supprimée.", "success")
    return redirect(url_for('suggestions.index'))
