"""
Routes de gestion des tickets pour CosmiCenter
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from html import escape
from models import (db, Ticket, Utilisateur, Departement, CategorieTicket, Commentaire, HistoriqueTicket,
                    Tache, PieceJointe, Notification)
from services.email_service import send_email_notification
from utils.permissions import (visible_tickets_query, can_access_ticket, can_manage_ticket, role_level)
from utils.uploads import save_upload, UploadError, MAX_ATTACHMENT_BYTES
from datetime import datetime, timedelta
import logging

# Créer le blueprint
tickets_bp = Blueprint('tickets', __name__)
logger = logging.getLogger(__name__)

STATUTS = ['nouveau', 'ouvert', 'en_cours', 'en_attente', 'resolu', 'ferme', 'annule']
STATUTS_OUVERTS = ['nouveau', 'ouvert']          # « ouvert » est un ancien synonyme de « nouveau »
PRIORITES = ['critique', 'urgente', 'haute', 'moyenne', 'basse']
TYPES_STANDARD = ['incident', 'demande', 'besoin', 'tache', 'plainte']
SORTABLE = {
    'date_creation': Ticket.date_creation,
    'date_modification': Ticket.date_modification,
    'date_echeance': Ticket.date_echeance,
    'titre': Ticket.titre,
    'statut': Ticket.statut,
    'priorite': Ticket.priorite,
    'type_ticket': Ticket.type_ticket,
    'numero': Ticket.numero,
    'id': Ticket.numero,
}
MAX_TITRE = 200
MAX_TEXT = 20000
MAX_COMMENT = 10000


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', set())


def _public_url(endpoint, **values):
    """URL absolue d'une page (PUBLIC_BASE_URL si défini, sinon l'hôte de la requête courante)."""
    base = current_app.config.get('PUBLIC_BASE_URL')
    if base:
        return base + url_for(endpoint, **values)
    return url_for(endpoint, _external=True, **values)


def _save_attachments(ticket, commentaire=None):
    """Enregistre les fichiers du champ « attachments » ; retourne la liste des messages d'erreur."""
    errors = []
    for f in request.files.getlist('attachments'):
        if not f or not f.filename:
            continue
        try:
            stored, original, size = save_upload(
                f, 'tickets', current_app.config['ALLOWED_EXTENSIONS'], MAX_ATTACHMENT_BYTES)
        except UploadError as exc:
            errors.append(str(exc))
            continue
        db.session.add(PieceJointe(
            ticket_id=ticket.id,
            commentaire_id=commentaire.id if commentaire else None,
            nom_fichier=stored,
            nom_original=original,
            type_mime=f.content_type,
            taille=size,
            chemin=f'uploads/tickets/{stored}',
            uploade_par_id=current_user.id
        ))
    return errors


def _apply_status(ticket, new_status):
    """Applique un statut et tient à jour les dates / durées associées."""
    now = datetime.utcnow()
    ticket.statut = new_status
    if new_status == 'resolu':
        if not ticket.date_resolution:
            ticket.date_resolution = now
        if ticket.date_creation:
            ticket.temps_resolution_minutes = int((ticket.date_resolution - ticket.date_creation).total_seconds() // 60)
        if ticket.date_echeance:
            ticket.sla_respecte = ticket.date_resolution <= ticket.date_echeance
    elif new_status == 'ferme':
        ticket.date_fermeture = now
    elif new_status in ('nouveau', 'ouvert', 'en_cours', 'en_attente'):
        ticket.date_fermeture = None
        if new_status != 'en_attente':
            ticket.date_resolution = None
            ticket.temps_resolution_minutes = None


def _filtered_listing(base_query, page_title):
    """Filtres / tri / pagination communs aux listes « Tous les tickets » et « Mes tickets »."""
    statut = request.args.get('statut')
    priorite = request.args.get('priorite')
    departement_id = request.args.get('departement_id')

    query = base_query
    if statut:
        if statut in STATUTS_OUVERTS:
            query = query.filter(Ticket.statut.in_(STATUTS_OUVERTS))
        else:
            query = query.filter(Ticket.statut == statut)
    if priorite:
        query = query.filter(Ticket.priorite == priorite)
    if departement_id:
        query = query.filter(Ticket.departement_id == departement_id)

    sort_column = SORTABLE.get(request.args.get('sort_by', 'date_creation'), Ticket.date_creation)
    if request.args.get('order', 'desc') == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    page = request.args.get('page', 1, type=int)
    tickets = query.paginate(page=page, per_page=20, error_out=False)
    departements = Departement.query.filter_by(actif=True).all()

    # Tickets déjà consultés par l'utilisateur courant
    viewed_ticket_ids = []
    if tickets.items:
        viewed_ticket_ids = [
            h.ticket_id for h in HistoriqueTicket.query.filter(
                HistoriqueTicket.utilisateur_id == current_user.id,
                HistoriqueTicket.action == 'Consultation',
                HistoriqueTicket.ticket_id.in_([t.id for t in tickets.items])
            ).all()
        ]

    return render_template('tickets/liste.html',
                           tickets=tickets,
                           departements=departements,
                           page_title=page_title,
                           viewed_ticket_ids=viewed_ticket_ids)


@tickets_bp.route('/tableau-bord')
@login_required
def tableau_bord():
    """Tableau de bord principal"""
    base_query = visible_tickets_query(current_user)

    stats = {
        'total': base_query.count(),
        'ouvert': base_query.filter(Ticket.statut.in_(STATUTS_OUVERTS)).count(),
        'en_cours': base_query.filter(Ticket.statut == 'en_cours').count(),
        'resolu': base_query.filter(Ticket.statut == 'resolu').count(),
    }

    # Tickets récents
    tickets_recents = base_query.order_by(Ticket.date_creation.desc()).limit(100).all()

    # Tickets urgents (priorité haute/urgente/critique et non clos)
    tickets_urgents = base_query.filter(
        Ticket.statut.notin_(['resolu', 'ferme', 'annule']),
        Ticket.priorite.in_(['haute', 'urgente', 'critique'])
    ).order_by(Ticket.date_creation.desc()).limit(5).all()

    return render_template('tickets/tableau_bord.html',
                           stats=stats,
                           tickets=tickets_recents,
                           tickets_urgents=tickets_urgents)


@tickets_bp.route('/liste')
@login_required
def liste():
    """Liste de tous les tickets visibles par l'utilisateur"""
    return _filtered_listing(visible_tickets_query(current_user), "Tous les tickets")


@tickets_bp.route('/mes-tickets')
@login_required
def mes_tickets():
    """Liste de mes tickets (créés, assignés, département, collaboration)"""
    from utils.permissions import ticket_visibility_filter
    return _filtered_listing(Ticket.query.filter(ticket_visibility_filter(current_user)), "Mes tickets")


def _form_context():
    departements = Departement.query.filter_by(actif=True).order_by(Departement.nom).all()
    utilisateurs = sorted(
        Utilisateur.query.filter_by(actif=True).all(),
        key=lambda u: (u.nom_complet or '').strip().upper()
    )
    categories = CategorieTicket.query.filter_by(actif=True).order_by(CategorieTicket.nom).all()
    return departements, utilisateurs, categories


def _read_ticket_fields(default_type='demande'):
    """Lit et valide les champs communs création / modification. Retourne (valeurs, erreurs)."""
    errors = []
    titre = (request.form.get('titre') or '').strip()
    description = (request.form.get('description') or '').strip()
    priorite = request.form.get('priorite', 'moyenne')
    type_ticket = request.form.get('type_ticket', default_type)
    if type_ticket == 'autre':
        type_ticket = (request.form.get('custom_type') or '').strip()[:20] or 'autre'
    elif type_ticket not in TYPES_STANDARD:
        errors.append('Type de ticket invalide.')

    if not titre:
        errors.append('Le résumé du problème est obligatoire.')
    elif len(titre) > MAX_TITRE:
        errors.append(f'Le résumé ne doit pas dépasser {MAX_TITRE} caractères.')
    if not description:
        errors.append('La description est obligatoire.')
    elif len(description) > MAX_TEXT:
        errors.append(f'La description ne doit pas dépasser {MAX_TEXT} caractères.')
    if priorite not in PRIORITES:
        errors.append('Priorité invalide.')

    return {'titre': titre, 'description': description, 'priorite': priorite, 'type_ticket': type_ticket}, errors


def _valid_department_id(value):
    value = value or None
    if value and not db.session.get(Departement, value):
        return None, False
    return value, True


@tickets_bp.route('/nouveau', methods=['GET', 'POST'])
@login_required
def nouveau():
    """Créer un nouveau ticket"""
    if request.method == 'POST':
        fields, errors = _read_ticket_fields()
        routing_type = request.form.get('routing_type', 'all')
        departement_id, dept_ok = _valid_department_id(request.form.get('departement_id'))
        if not dept_ok:
            errors.append('Département introuvable.')

        assigne_id = None
        if routing_type == 'specific':
            assigne_id = request.form.get('assigne_a_id') or None
            if assigne_id:
                assignee = db.session.get(Utilisateur, assigne_id)
                if not assignee or not assignee.actif:
                    errors.append("L'agent assigné est introuvable ou inactif.")

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return _render_nouveau()

        try:
            ticket = Ticket(
                numero=Ticket.generer_numero(),
                titre=fields['titre'],
                description=fields['description'],
                type_ticket=fields['type_ticket'],
                priorite=fields['priorite'],
                departement_id=departement_id,
                assigne_a_id=assigne_id,
                createur_id=current_user.id
            )

            categorie_id = request.form.get('categorie_id') or None
            if categorie_id:
                cat = db.session.get(CategorieTicket, categorie_id)
                if cat:
                    ticket.categorie_id = cat.id
                    if cat.delai_resolution_jours:
                        ticket.date_echeance = datetime.utcnow() + timedelta(days=cat.delai_resolution_jours)

            db.session.add(ticket)
            db.session.flush()  # obtenir l'ID du ticket

            if routing_type == 'collab':
                for dept_id in request.form.getlist('collab_departements[]'):
                    dept = db.session.get(Departement, dept_id) if dept_id else None
                    if dept:
                        ticket.departements_collab.append(dept)
                for user_id in request.form.getlist('collab_users[]'):
                    user = db.session.get(Utilisateur, user_id) if user_id else None
                    if user and user.actif:
                        ticket.collaborateurs.append(user)

            # Sous-tâches (checklist)
            for i, titre in enumerate(request.form.getlist('taches[]')):
                titre = titre.strip()[:200]
                if titre:
                    db.session.add(Tache(ticket_id=ticket.id, titre=titre, ordre=i))

            upload_errors = _save_attachments(ticket)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la création du ticket: {e}', exc_info=True)
            flash('Erreur lors de la création du ticket', 'danger')
            return _render_nouveau()

        flash('Ticket créé avec succès', 'success')
        for msg in upload_errors:
            flash(msg, 'warning')
        logger.info(f'Nouveau ticket créé: {ticket.numero} par {current_user.email}')

        # Notifications : le ticket est déjà enregistré, un échec ici ne doit pas l'annuler
        try:
            _notify_new_ticket(ticket)
        except Exception as e:
            db.session.rollback()
            logger.error(f'Notification du ticket {ticket.numero} impossible: {e}', exc_info=True)

        return redirect(url_for('tickets.detail', ticket_id=ticket.id))

    return _render_nouveau()


def _render_nouveau():
    departements, utilisateurs, categories = _form_context()
    return render_template('tickets/nouveau.html',
                           departements=departements,
                           categories=categories,
                           utilisateurs=utilisateurs)


def _notify_new_ticket(ticket):
    users_to_notify = set()

    if ticket.assigne_a_id:
        assignee = db.session.get(Utilisateur, ticket.assigne_a_id)
        if assignee and assignee.actif:
            users_to_notify.add(assignee)
    elif ticket.departement_id:
        dept = db.session.get(Departement, ticket.departement_id)
        if dept:
            for user in dept.membres:
                if user.actif:
                    users_to_notify.add(user)

    for collab_user in ticket.collaborateurs:
        if collab_user.actif:
            users_to_notify.add(collab_user)
    for collab_dept in ticket.departements_collab:
        for user in collab_dept.membres:
            if user.actif:
                users_to_notify.add(user)

    users_to_notify.discard(current_user._get_current_object())

    recipients = [current_user.email] + [u.email for u in users_to_notify]
    send_email_notification(
        current_app._get_current_object(),
        f"Ticket : [#{ticket.numero}] {ticket.titre}",
        recipients,
        render_template('emails/nouveau_ticket.html', ticket=ticket,
                        ticket_url=_public_url('tickets.detail', ticket_id=ticket.id))
    )

    for user in users_to_notify:
        db.session.add(Notification(
            utilisateur_id=user.id,
            titre="Nouveau ticket",
            message=f'Le ticket "{ticket.titre}" vous concerne.',
            type_notification="ticket",
            lien=url_for('tickets.detail', ticket_id=ticket.id)
        ))
    db.session.commit()


@tickets_bp.route('/<ticket_id>')
@login_required
def detail(ticket_id):
    """Détail d'un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    # Vérifier les permissions AVANT toute écriture (consultation, notifications)
    if not can_access_ticket(current_user, ticket):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('tickets.liste'))

    # Marquer comme lues les notifications liées à ce ticket
    ticket_url = url_for('tickets.detail', ticket_id=ticket.id)
    marked_any = False
    for notif in Notification.query.filter_by(utilisateur_id=current_user.id, lue=False).all():
        if notif.lien and ticket_url in notif.lien:
            notif.lue = True
            notif.date_lecture = datetime.utcnow()
            marked_any = True

    # Journaliser la première consultation (retire la mise en évidence « non lu » pour cet utilisateur)
    hist_exists = HistoriqueTicket.query.filter_by(
        ticket_id=ticket.id,
        utilisateur_id=current_user.id,
        action='Consultation'
    ).first()
    if not hist_exists:
        db.session.add(HistoriqueTicket(
            ticket_id=ticket.id,
            utilisateur_id=current_user.id,
            action='Consultation',
            details='Ticket consulté'
        ))
        marked_any = True

    if marked_any:
        db.session.commit()

    commentaires = Commentaire.query.filter_by(ticket_id=ticket_id)\
        .order_by(Commentaire.date_creation.asc()).all()

    # Utilisateurs assignables (département du ticket + départements en collaboration)
    allowed_dept_ids = set()
    if ticket.departement_id:
        allowed_dept_ids.add(ticket.departement_id)
    for cd in ticket.departements_collab:
        allowed_dept_ids.add(cd.id)

    if allowed_dept_ids:
        users_query = Utilisateur.query.filter(
            Utilisateur.actif == True,  # noqa: E712
            Utilisateur.departement_id.in_(list(allowed_dept_ids))
        )
    else:
        users_query = Utilisateur.query.filter_by(actif=True)

    assignable_users = set(users_query.all())
    for c_user in ticket.collaborateurs:
        if c_user.actif:
            assignable_users.add(c_user)
    if ticket.assigne_a:
        assignable_users.add(ticket.assigne_a)

    utilisateurs = sorted(list(assignable_users), key=lambda u: (u.nom_complet or '').strip().upper())

    return render_template('tickets/detail.html',
                           ticket=ticket,
                           commentaires=commentaires,
                           utilisateurs=utilisateurs)


@tickets_bp.route('/<ticket_id>/modifier', methods=['GET', 'POST'])
@login_required
def modifier(ticket_id):
    """Modifier un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    # Seul le créateur, un manager/admin ou un détenteur de tickets.modifier peut modifier les détails
    est_admin = role_level(current_user) >= 70 or current_user.has_permission('tickets.modifier')
    if not est_admin and ticket.createur_id != current_user.id:
        flash("Seul le créateur du ticket peut en modifier les détails. Les agents peuvent uniquement changer le statut.", "danger")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    if request.method == 'POST':
        fields, errors = _read_ticket_fields()
        new_statut = request.form.get('statut', ticket.statut)
        if new_statut not in STATUTS:
            errors.append('Statut invalide.')
        new_dept_id, dept_ok = _valid_department_id(request.form.get('departement_id'))
        if not dept_ok:
            errors.append('Département introuvable.')
        routing_type = request.form.get('routing_type', 'all')
        new_ass_id = (request.form.get('assigne_a_id') or None) if routing_type == 'specific' else None
        new_ass = db.session.get(Utilisateur, new_ass_id) if new_ass_id else None
        if new_ass_id and (not new_ass or not new_ass.actif):
            errors.append("L'agent assigné est introuvable ou inactif.")
        new_cat_id = request.form.get('categorie_id') or None
        new_cat = db.session.get(CategorieTicket, new_cat_id) if new_cat_id else None
        if new_cat_id and not new_cat:
            errors.append('Catégorie introuvable.')

        if errors:
            for msg in errors:
                flash(msg, 'danger')
            return _render_modifier(ticket)

        try:
            changes = []
            if ticket.titre != fields['titre']:
                changes.append(('Titre', ticket.titre, fields['titre']))
            if ticket.type_ticket != fields['type_ticket']:
                changes.append(('Type', ticket.type_ticket, fields['type_ticket']))
            if ticket.priorite != fields['priorite']:
                changes.append(('Priorité', ticket.priorite, fields['priorite']))
            if ticket.statut != new_statut:
                changes.append(('Statut', ticket.statut, new_statut))
            if (ticket.description or '') != fields['description']:
                changes.append(('Description', 'Modifiée', 'Nouvelle description'))

            if str(ticket.categorie_id or '') != str(new_cat_id or ''):
                old_cat = ticket.categorie.nom if ticket.categorie else 'Aucune'
                changes.append(('Catégorie', old_cat, new_cat.nom if new_cat else 'Aucune'))
                if new_cat and new_cat.delai_resolution_jours and not ticket.date_echeance:
                    ticket.date_echeance = datetime.utcnow() + timedelta(days=new_cat.delai_resolution_jours)
            ticket.categorie_id = new_cat_id

            if str(ticket.departement_id or '') != str(new_dept_id or ''):
                new_dept = db.session.get(Departement, new_dept_id) if new_dept_id else None
                old_dept = ticket.departement_associe.nom if ticket.departement_associe else None
                changes.append(('Département', old_dept, new_dept.nom if new_dept else None))

            if routing_type == 'specific' and str(ticket.assigne_a_id or '') != str(new_ass_id or ''):
                old_ass = ticket.assigne_a.nom_complet if ticket.assigne_a else 'Non assigné'
                changes.append(('Assigné à', old_ass, new_ass.nom_complet if new_ass else 'Non assigné'))
                if new_ass and str(new_ass.id) != str(current_user.id):
                    db.session.add(Notification(
                        utilisateur_id=new_ass.id,
                        titre="Nouveau ticket assigné",
                        message=f'Le ticket "{fields["titre"]}" vous a été assigné.',
                        type_notification="ticket",
                        lien=url_for('tickets.detail', ticket_id=ticket.id)
                    ))
            elif routing_type != 'specific' and ticket.assigne_a_id:
                changes.append(('Assigné à', ticket.assigne_a.nom_complet, 'Non assigné'))

            for champ, old_val, new_val in changes:
                db.session.add(HistoriqueTicket(
                    ticket_id=ticket.id,
                    utilisateur_id=current_user.id,
                    action=f"Modification: {champ}",
                    champ_modifie=champ,
                    ancienne_valeur=old_val,
                    nouvelle_valeur=new_val
                ))

            ticket.titre = fields['titre']
            ticket.description = fields['description']
            ticket.priorite = fields['priorite']
            ticket.type_ticket = fields['type_ticket']
            ticket.departement_id = new_dept_id
            if ticket.statut != new_statut:
                _apply_status(ticket, new_statut)

            # Routage
            if routing_type == 'specific':
                ticket.assigne_a_id = new_ass_id
                ticket.collaborateurs.clear()
                ticket.departements_collab.clear()
            elif routing_type == 'collab':
                ticket.assigne_a_id = None
                ticket.departements_collab.clear()
                for dept_id in request.form.getlist('collab_departements[]'):
                    dept = db.session.get(Departement, dept_id) if dept_id else None
                    if dept:
                        ticket.departements_collab.append(dept)
                ticket.collaborateurs.clear()
                for user_id in request.form.getlist('collab_users[]'):
                    user = db.session.get(Utilisateur, user_id) if user_id else None
                    if user and user.actif:
                        ticket.collaborateurs.append(user)
            else:  # 'all'
                ticket.assigne_a_id = None
                ticket.collaborateurs.clear()
                ticket.departements_collab.clear()

            # Checklist existante (titres + état) puis nouveaux éléments
            taches_terminees = set(request.form.getlist('taches_terminees[]'))
            taches_existantes = {k.split('[')[1].rstrip(']'): v
                                 for k, v in request.form.items()
                                 if k.startswith('taches_existantes[')}
            submitted_ids = set(taches_existantes.keys())

            for tache in list(ticket.taches):
                if tache.id in submitted_ids:
                    titre = taches_existantes[tache.id].strip()[:200]
                    if titre:
                        tache.titre = titre
                        tache.terminee = tache.id in taches_terminees
                        if tache.terminee and not tache.date_completion:
                            tache.date_completion = datetime.utcnow()
                        elif not tache.terminee:
                            tache.date_completion = None
                    else:
                        db.session.delete(tache)
                else:
                    db.session.delete(tache)  # retirée du formulaire (×)

            max_ordre = max((t.ordre or 0 for t in ticket.taches), default=-1) + 1
            for i, titre in enumerate(request.form.getlist('taches[]')):
                titre = titre.strip()[:200]
                if titre:
                    db.session.add(Tache(ticket_id=ticket.id, titre=titre, ordre=max_ordre + i))

            upload_errors = _save_attachments(ticket)

            db.session.commit()
            flash('Ticket modifié avec succès', 'success')
            for msg in upload_errors:
                flash(msg, 'warning')
            logger.info(f'Ticket modifié: {ticket.numero} par {current_user.email}')
            return redirect(url_for('tickets.detail', ticket_id=ticket_id))

        except Exception as e:
            db.session.rollback()
            logger.error(f'Erreur lors de la modification du ticket: {e}', exc_info=True)
            flash('Erreur lors de la modification', 'danger')

    return _render_modifier(ticket)


def _render_modifier(ticket):
    departements, utilisateurs, categories = _form_context()
    return render_template('tickets/modifier.html',
                           ticket=ticket,
                           departements=departements,
                           categories=categories,
                           utilisateurs=utilisateurs)


@tickets_bp.route('/<ticket_id>/commenter', methods=['POST'])
@login_required
def commenter(ticket_id):
    """Ajouter un commentaire à un ticket"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if not can_access_ticket(current_user, ticket):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('tickets.liste'))

    contenu = (request.form.get('contenu') or '').strip()
    if not contenu:
        flash('Le commentaire ne peut pas être vide.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))
    if len(contenu) > MAX_COMMENT:
        flash(f'Le commentaire ne doit pas dépasser {MAX_COMMENT} caractères.', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    interne = request.form.get('interne') in ('on', '1', 'true', 'True') and can_manage_ticket(current_user, ticket)

    try:
        commentaire = Commentaire(
            ticket_id=ticket.id,
            auteur_id=current_user.id,
            contenu=contenu,
            interne=interne
        )
        db.session.add(commentaire)
        db.session.flush()

        # Première réponse d'un agent (≠ créateur) : alimente les statistiques SLA
        if ticket.date_premiere_reponse is None and current_user.id != ticket.createur_id:
            ticket.date_premiere_reponse = datetime.utcnow()
            if ticket.date_creation:
                ticket.temps_premiere_reponse_minutes = int(
                    (ticket.date_premiere_reponse - ticket.date_creation).total_seconds() // 60)

        upload_errors = _save_attachments(ticket, commentaire)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erreur lors de l'ajout du commentaire: {e}", exc_info=True)
        flash("Erreur lors de l'ajout du commentaire", 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    flash('Commentaire ajouté', 'success')
    for msg in upload_errors:
        flash(msg, 'warning')
    logger.info(f'Commentaire ajouté au ticket {ticket.numero} par {current_user.email}')

    if not interne:
        try:
            recipients = {ticket.createur.email}
            if ticket.assigne_a:
                recipients.add(ticket.assigne_a.email)
            recipients.discard(current_user.email)
            if recipients:
                send_email_notification(
                    current_app._get_current_object(),
                    f"Nouveau commentaire : [#{ticket.numero}] {ticket.titre}",
                    list(recipients),
                    f"<p>Un nouveau commentaire a été ajouté au ticket <b>#{escape(ticket.numero)}</b> "
                    f"par {escape(current_user.prenom)}.</p>"
                    f"<p><i>{escape(contenu)}</i></p>"
                    f"<p><a href='{escape(_public_url('tickets.detail', ticket_id=ticket.id))}'>Voir le ticket</a></p>"
                )
        except Exception as e:
            logger.error(f"Notification du commentaire impossible: {e}")

    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/<ticket_id>/statut', methods=['POST'])
@login_required
def changer_statut(ticket_id):
    """Mettre à jour rapidement le statut ou l'assignation d'un ticket depuis la barre latérale"""
    ticket = Ticket.query.get_or_404(ticket_id)

    if not can_access_ticket(current_user, ticket) or not can_manage_ticket(current_user, ticket):
        flash("Vous n'êtes pas autorisé à modifier ce ticket.", "danger")
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    nouveau_statut = request.form.get('statut')
    nouvel_assigne = request.form.get('assigne_a_id')

    try:
        modifie = False
        if nouveau_statut:
            if nouveau_statut not in STATUTS:
                flash('Statut invalide.', 'danger')
                return redirect(url_for('tickets.detail', ticket_id=ticket_id))
            if ticket.statut != nouveau_statut:
                db.session.add(HistoriqueTicket(
                    ticket_id=ticket.id, utilisateur_id=current_user.id, action='Modification de statut',
                    champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur=nouveau_statut))
                _apply_status(ticket, nouveau_statut)
                modifie = True

        # Assignation : réservée à la permission tickets.assigner
        if nouvel_assigne is not None and current_user.has_permission('tickets.assigner'):
            nouvel_assigne_val = nouvel_assigne or None
            nouvel_user = db.session.get(Utilisateur, nouvel_assigne_val) if nouvel_assigne_val else None
            if nouvel_assigne_val and (not nouvel_user or not nouvel_user.actif):
                flash("Utilisateur introuvable ou inactif.", 'danger')
                return redirect(url_for('tickets.detail', ticket_id=ticket_id))
            if ticket.assigne_a_id != nouvel_assigne_val:
                ancien_nom = ticket.assigne_a.nom_complet if ticket.assigne_a else 'Non assigné'
                nouveau_nom = nouvel_user.nom_complet if nouvel_user else 'Non assigné'
                if nouvel_user and str(nouvel_user.id) != str(current_user.id):
                    db.session.add(Notification(
                        utilisateur_id=nouvel_user.id,
                        titre="Nouveau ticket assigné",
                        message=f'Le ticket "{ticket.titre}" vous a été assigné.',
                        type_notification="ticket",
                        lien=url_for('tickets.detail', ticket_id=ticket.id)
                    ))
                db.session.add(HistoriqueTicket(
                    ticket_id=ticket.id, utilisateur_id=current_user.id, action="Changement d'assignation",
                    champ_modifie='Assigné à', ancienne_valeur=ancien_nom, nouvelle_valeur=nouveau_nom))
                ticket.assigne_a_id = nouvel_assigne_val
                modifie = True

        if modifie:
            db.session.commit()
            flash('Le ticket a été mis à jour.', 'success')
            logger.info(f"Ticket {ticket.numero} mis à jour via action rapide par {current_user.email}")

    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur lors de la mise à jour rapide: {e}', exc_info=True)
        flash('Erreur lors de la mise à jour.', 'danger')

    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


def _close_or_reopen(ticket_id, target_status, action_label, ok_message):
    ticket = Ticket.query.get_or_404(ticket_id)

    if not can_access_ticket(current_user, ticket) or not can_manage_ticket(current_user, ticket):
        flash('Accès non autorisé', 'danger')
        return redirect(url_for('tickets.detail', ticket_id=ticket_id))

    try:
        db.session.add(HistoriqueTicket(
            ticket_id=ticket.id, utilisateur_id=current_user.id, action=action_label,
            champ_modifie='Statut', ancienne_valeur=ticket.statut, nouvelle_valeur=target_status))
        _apply_status(ticket, target_status)
        db.session.commit()
        flash(ok_message, 'success')
        logger.info(f'{action_label}: {ticket.numero} par {current_user.email}')
    except Exception as e:
        db.session.rollback()
        logger.error(f'{action_label} impossible: {e}', exc_info=True)
        flash('Une erreur est survenue', 'danger')
    return redirect(url_for('tickets.detail', ticket_id=ticket_id))


@tickets_bp.route('/<ticket_id>/fermer', methods=['POST'])
@login_required
def fermer(ticket_id):
    """Fermer un ticket"""
    return _close_or_reopen(ticket_id, 'ferme', 'Fermeture de ticket', 'Ticket fermé')


@tickets_bp.route('/<ticket_id>/reouvrir', methods=['POST'])
@login_required
def reouvrir(ticket_id):
    """Réouvrir un ticket fermé"""
    return _close_or_reopen(ticket_id, 'en_cours', 'Réouverture de ticket', 'Ticket réouvert avec succès')


@tickets_bp.route('/tache/<tache_id>/toggle', methods=['POST'])
@login_required
def toggle_tache(tache_id):
    """Marquer une sous-tâche comme terminée ou non"""
    tache = Tache.query.get_or_404(tache_id)
    ticket = tache.ticket

    if not can_access_ticket(current_user, ticket):
        return jsonify({'error': 'Accès non autorisé'}), 403

    try:
        tache.terminee = not tache.terminee
        tache.date_completion = datetime.utcnow() if tache.terminee else None
        db.session.commit()
        return jsonify({'success': True, 'terminee': tache.terminee})
    except Exception as e:
        db.session.rollback()
        logger.error(f'Erreur toggle tâche: {e}', exc_info=True)
        return jsonify({'error': 'Erreur serveur'}), 500


# ─── Base de connaissances (FAQ) ────────────────────────────────────────────

@tickets_bp.route('/faq')
@login_required
def faq_liste():
    """Liste des guides de la base de connaissances"""
    return render_template('faq/liste.html')


@tickets_bp.route('/faq/<article_id>')
@login_required
def faq_detail(article_id):
    """Lecture d'un article de la base de connaissances"""
    return render_template('faq/detail.html')


# ─── Chat / Messagerie ───────────────────────────────────────────────────────

@tickets_bp.route('/chat')
@login_required
def chat_inbox():
    """Centre de messagerie"""
    unread_chat_notifs = Notification.query.filter_by(
        utilisateur_id=current_user.id,
        type_notification='chat',
        lue=False
    ).all()

    if unread_chat_notifs:
        for notif in unread_chat_notifs:
            notif.lue = True
            notif.date_lecture = datetime.utcnow()
        db.session.commit()

    return render_template('chat/inbox.html')
