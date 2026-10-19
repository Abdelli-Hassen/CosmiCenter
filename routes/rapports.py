from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps
from utils.security import csv_safe
import io
import csv

rapports_bp = Blueprint('rapports', __name__)

PERIODES = {'7j': 7, '30j': 30, '90j': 90, '1a': 365}
STATUTS_OUVERTS = ['nouveau', 'ouvert', 'en_cours', 'en_attente']


def permission_required(permission_name):
    """Restreint l'accès selon une permission (les rôles de niveau 100 passent implicitement)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.connexion'))
            if not current_user.has_permission(permission_name):
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('tickets.tableau_bord'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _periode(default='30j'):
    """(code de période, date de fin, date de début) à partir du paramètre ?periode=."""
    periode = request.args.get('periode', default)
    if periode not in PERIODES:
        periode = default if default in PERIODES else '30j'
    date_fin = datetime.now()
    return periode, date_fin, date_fin - timedelta(days=PERIODES[periode])


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@rapports_bp.route('/')
@login_required
@permission_required('rapports_globaux.voir')
def tableau_bord():
    """Tableau de bord principal des rapports"""
    periode, date_fin, date_debut = _periode()

    stats_globales = {
        'total_tickets': Ticket.query.filter(Ticket.date_creation >= date_debut).count(),
        'tickets_ouverts': Ticket.query.filter(Ticket.statut.in_(STATUTS_OUVERTS)).count(),
        'tickets_resolus': Ticket.query.filter(
            Ticket.statut == 'resolu',
            Ticket.date_resolution >= date_debut
        ).count(),
        'tickets_fermes': Ticket.query.filter(
            Ticket.statut == 'ferme',
            Ticket.date_fermeture >= date_debut
        ).count(),
        'utilisateurs_actifs': Utilisateur.query.filter_by(actif=True).count(),
        'departements_actifs': Departement.query.filter_by(actif=True).count(),
    }

    def grouped(column):
        return db.session.query(column, func.count(Ticket.id)).filter(
            Ticket.date_creation >= date_debut).group_by(column).all()

    tickets_par_statut = grouped(Ticket.statut)
    tickets_par_priorite = grouped(Ticket.priorite)
    tickets_par_type = grouped(Ticket.type_ticket)

    tickets_par_departement = db.session.query(
        Departement.nom, func.count(Ticket.id)
    ).join(
        Departement, Ticket.departement_id == Departement.id
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(Departement.nom).all()

    evolution_tickets = db.session.query(
        db.cast(Ticket.date_creation, db.Date).label('date'),
        func.count(Ticket.id).label('count')
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(db.cast(Ticket.date_creation, db.Date)).order_by(db.cast(Ticket.date_creation, db.Date)).all()

    # Durées stockées en minutes, affichées en heures ; None (« — ») lorsqu'il n'y a aucune donnée
    avg_resolution = db.session.query(
        func.avg(Ticket.temps_resolution_minutes)
    ).filter(
        Ticket.date_resolution >= date_debut,
        Ticket.temps_resolution_minutes.isnot(None)
    ).scalar()
    temps_moyen_resolution = float(avg_resolution) / 60 if avg_resolution is not None else None

    avg_reponse = db.session.query(
        func.avg(Ticket.temps_premiere_reponse_minutes)
    ).filter(
        Ticket.date_premiere_reponse >= date_debut,
        Ticket.temps_premiere_reponse_minutes.isnot(None)
    ).scalar()
    temps_moyen_premiere_reponse = float(avg_reponse) / 60 if avg_reponse is not None else None

    avg_satisfaction = db.session.query(
        func.avg(Ticket.satisfaction)
    ).filter(
        Ticket.satisfaction.isnot(None),
        Ticket.date_fermeture >= date_debut
    ).scalar()
    satisfaction_moyenne = float(avg_satisfaction) if avg_satisfaction is not None else None

    # Top 10 des agents par tickets résolus
    top_agents = db.session.query(
        Utilisateur.nom,
        Utilisateur.prenom,
        func.count(Ticket.id).label('count')
    ).join(
        Ticket, Ticket.assigne_a_id == Utilisateur.id
    ).filter(
        Ticket.date_resolution >= date_debut,
        Ticket.statut == 'resolu'
    ).group_by(
        Utilisateur.id, Utilisateur.nom, Utilisateur.prenom
    ).order_by(
        func.count(Ticket.id).desc()
    ).limit(10).all()

    # SLA - taux de respect
    tickets_avec_sla = Ticket.query.filter(
        Ticket.date_creation >= date_debut,
        Ticket.sla_respecte.isnot(None)
    ).count()
    tickets_sla_respecte = Ticket.query.filter(
        Ticket.date_creation >= date_debut,
        Ticket.sla_respecte == True  # noqa: E712
    ).count()
    taux_sla = (tickets_sla_respecte / tickets_avec_sla * 100) if tickets_avec_sla > 0 else None

    return render_template('rapports/tableau_bord.html',
                           periode=periode,
                           date_debut=date_debut,
                           date_fin=date_fin,
                           stats_globales=stats_globales,
                           tickets_par_statut=dict(tickets_par_statut),
                           tickets_par_priorite=dict(tickets_par_priorite),
                           tickets_par_type=dict(tickets_par_type),
                           tickets_par_departement=dict(tickets_par_departement),
                           evolution_tickets=evolution_tickets,
                           temps_moyen_resolution=temps_moyen_resolution,
                           temps_moyen_premiere_reponse=temps_moyen_premiere_reponse,
                           satisfaction_moyenne=satisfaction_moyenne,
                           top_agents=top_agents,
                           taux_sla=taux_sla)


def _agent_stats(tickets):
    resolus = [t for t in tickets if t.statut == 'resolu']
    en_cours = [t for t in tickets if t.statut in STATUTS_OUVERTS]
    temps = [t.temps_resolution_minutes for t in resolus if t.temps_resolution_minutes is not None]
    notes = [t.satisfaction for t in resolus if t.satisfaction is not None]
    # temps en minutes -> heures (les gabarits affichent des heures)
    return resolus, en_cours, (sum(temps) / len(temps) / 60 if temps else 0), (sum(notes) / len(notes) if notes else 0)


@rapports_bp.route('/performance-agents')
@login_required
@permission_required('rapports_performance.voir')
def performance_agents():
    """Rapport de performance des agents"""
    periode, date_fin, date_debut = _periode()

    # Un seul chargement des tickets de la période, regroupés par agent
    tickets_by_agent = {}
    for t in Ticket.query.filter(Ticket.assigne_a_id.isnot(None), Ticket.date_creation >= date_debut).all():
        tickets_by_agent.setdefault(t.assigne_a_id, []).append(t)

    # « Agents » = utilisateurs qui traitent des tickets : rôle autorisé à modifier/clôturer les tickets,
    # ou ayant des tickets assignés sur la période (le personnel de point de vente n'est pas classé)
    agents = [u for u in Utilisateur.query.filter_by(actif=True).all()
              if u.id in tickets_by_agent or u.has_permission('tickets.modifier') or u.has_permission('tickets.cloturer')]
    stats_agents = []
    for agent in agents:
        tickets_assignes = tickets_by_agent.get(agent.id, [])
        tickets_resolus, tickets_en_cours, temps_moyen, satisfaction_moyenne = _agent_stats(tickets_assignes)

        tickets_details = []
        for t in sorted(tickets_resolus, key=lambda x: x.date_resolution or datetime.min, reverse=True)[:5]:
            tickets_details.append({
                'id': t.id,
                'titre': t.titre,
                'date_creation': t.date_creation.strftime('%d/%m/%Y %H:%M'),
                'date_resolution': t.date_resolution.strftime('%d/%m/%Y %H:%M') if t.date_resolution else 'N/A',
                'heures': round(t.temps_resolution_minutes / 60, 1) if t.temps_resolution_minutes else 0
            })

        stats_agents.append({
            'agent': agent,
            'total_tickets': len(tickets_assignes),
            'tickets_resolus': len(tickets_resolus),
            'tickets_en_cours': len(tickets_en_cours),
            'temps_moyen_resolution': temps_moyen,
            'satisfaction_moyenne': satisfaction_moyenne,
            # None (affiché « — ») quand l'agent n'a aucun ticket : 0 % serait trompeur
            'taux_resolution': (len(tickets_resolus) / len(tickets_assignes) * 100) if tickets_assignes else None,
            'tickets_details': tickets_details
        })

    # Classement : résolus d'abord, puis tickets assignés, puis nom (ordre stable et lisible)
    stats_agents.sort(key=lambda x: (-x['tickets_resolus'], -x['total_tickets'], (x['agent'].nom_complet or '').upper()))
    for i, stat in enumerate(stats_agents):
        stat['rank'] = i + 1

    # Le podium n'a de sens que pour les agents ayant réellement résolu des tickets
    podium = [s for s in stats_agents if s['tickets_resolus'] > 0][:3]

    return render_template('rapports/performance_agents.html',
                           stats_agents=stats_agents,
                           top_3_agents=podium,
                           periode=periode,
                           date_debut=date_debut,
                           date_fin=date_fin)


@rapports_bp.route('/performance-agents/<string:agent_id>/tickets')
@login_required
@permission_required('rapports_performance.voir')
def agent_tickets(agent_id):
    """Vue détaillée de tous les tickets d'un agent"""
    agent = Utilisateur.query.get_or_404(agent_id)
    periode, date_fin, date_debut = _periode()

    tickets = Ticket.query.filter(
        Ticket.assigne_a_id == agent_id,
        Ticket.date_creation >= date_debut
    ).order_by(Ticket.date_creation.desc()).all()

    tickets_resolus, tickets_en_cours, temps_moyen, satisfaction_moyenne = _agent_stats(tickets)

    # Classement par nombre de tickets résolus (une seule requête groupée)
    counts = dict(db.session.query(Ticket.assigne_a_id, func.count(Ticket.id)).filter(
        Ticket.statut == 'resolu', Ticket.date_creation >= date_debut,
        Ticket.assigne_a_id.isnot(None)).group_by(Ticket.assigne_a_id).all())
    actifs = [u.id for u in Utilisateur.query.filter_by(actif=True).all()]
    ordre = sorted(actifs, key=lambda uid: counts.get(uid, 0), reverse=True)
    rank = ordre.index(agent_id) + 1 if agent_id in ordre else 0

    stats = {
        'total': len(tickets),
        'resolus': len(tickets_resolus),
        'en_cours': len(tickets_en_cours),
        'temps_moyen': temps_moyen,
        'satisfaction': satisfaction_moyenne,
        'taux_resolution': (len(tickets_resolus) / len(tickets) * 100) if tickets else 0,
        'rank': rank
    }

    return render_template('rapports/agent_tickets.html',
                           agent=agent,
                           tickets=tickets,
                           periode=periode,
                           stats=stats)


@rapports_bp.route('/satisfaction-client')
@login_required
@permission_required('rapports_globaux.voir')
def satisfaction_client():
    """Rapport de satisfaction client"""
    periode, date_fin, date_debut = _periode()

    tickets_evalues = Ticket.query.filter(
        Ticket.satisfaction.isnot(None),
        Ticket.date_fermeture >= date_debut
    ).all()

    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for ticket in tickets_evalues:
        distribution[ticket.satisfaction] = distribution.get(ticket.satisfaction, 0) + 1

    satisfactions = [t.satisfaction for t in tickets_evalues]
    satisfaction_moyenne = sum(satisfactions) / len(satisfactions) if satisfactions else 0

    satisfaction_par_dept = {}
    for dept in Departement.query.filter_by(actif=True).all():
        tickets_dept = [t for t in tickets_evalues if t.departement and t.departement.id == dept.id]
        if tickets_dept:
            satisfaction_par_dept[dept.nom] = sum(t.satisfaction for t in tickets_dept) / len(tickets_dept)

    commentaires_positifs = [t for t in tickets_evalues
                             if t.satisfaction >= 4 and t.commentaire_satisfaction][:10]
    commentaires_negatifs = [t for t in tickets_evalues
                             if t.satisfaction <= 2 and t.commentaire_satisfaction][:10]

    return render_template('rapports/satisfaction_client.html',
                           tickets_evalues=tickets_evalues,
                           distribution=distribution,
                           satisfaction_moyenne=satisfaction_moyenne,
                           satisfaction_par_dept=satisfaction_par_dept,
                           commentaires_positifs=commentaires_positifs,
                           commentaires_negatifs=commentaires_negatifs,
                           periode=periode,
                           date_debut=date_debut,
                           date_fin=date_fin)


@rapports_bp.route('/export/csv')
@login_required
@permission_required('rapports_globaux.voir')
def export_csv():
    """Exporter les tickets en CSV"""
    date_debut = _parse_iso(request.args.get('date_debut'))
    date_fin = _parse_iso(request.args.get('date_fin'))
    if (request.args.get('date_debut') and not date_debut) or (request.args.get('date_fin') and not date_fin):
        flash('Date invalide : utilisez le format AAAA-MM-JJ.', 'danger')
        return redirect(url_for('rapports.tableau_bord'))

    query = Ticket.query
    if date_debut:
        query = query.filter(Ticket.date_creation >= date_debut)
    if date_fin:
        query = query.filter(Ticket.date_creation <= date_fin)

    tickets = query.order_by(Ticket.date_creation.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Numéro', 'Titre', 'Type', 'Priorité', 'Statut',
        'Créateur', 'Assigné à', 'Département', 'Catégorie',
        'Date création', 'Date résolution', 'Satisfaction'
    ])

    for ticket in tickets:
        dept = ticket.departement
        writer.writerow([csv_safe(v) for v in [
            ticket.numero,
            ticket.titre,
            ticket.type_ticket,
            ticket.priorite,
            ticket.statut,
            ticket.createur.nom_complet if ticket.createur else '',
            ticket.assigne_a.nom_complet if ticket.assigne_a else '',
            dept.nom if dept else '',
            ticket.categorie.nom if ticket.categorie else '',
            ticket.date_creation.strftime('%d/%m/%Y %H:%M'),
            ticket.date_resolution.strftime('%d/%m/%Y %H:%M') if ticket.date_resolution else '',
            ticket.satisfaction or ''
        ]])

    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'tickets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@rapports_bp.route('/api/stats')
@login_required
@permission_required('rapports_globaux.voir')
def api_stats():
    """API pour obtenir des statistiques en JSON"""
    type_stat = request.args.get('type', 'general')
    periode, date_fin, date_debut = _periode()

    if type_stat == 'evolution':
        evolution = db.session.query(
            db.cast(Ticket.date_creation, db.Date).label('date'),
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.date_creation >= date_debut
        ).group_by(db.cast(Ticket.date_creation, db.Date)).order_by(db.cast(Ticket.date_creation, db.Date)).all()

        return jsonify({
            'dates': [str(e.date) for e in evolution],
            'counts': [e.count for e in evolution]
        })

    elif type_stat == 'statuts':
        statuts = db.session.query(
            Ticket.statut,
            func.count(Ticket.id)
        ).filter(
            Ticket.date_creation >= date_debut
        ).group_by(Ticket.statut).all()

        return jsonify({
            'labels': [s[0] for s in statuts],
            'values': [s[1] for s in statuts]
        })

    return jsonify({'error': 'Type de statistique non reconnu'}), 400
