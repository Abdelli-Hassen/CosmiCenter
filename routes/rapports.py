from flask import Blueprint, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, PointDeVente
from services import reporting
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
    """Rapport global : indicateurs, évolution, répartitions, SLA, backlog, agents, PDV, satisfaction"""
    f = reporting.parse_filters(request.args)
    rapport = reporting.build_report(f)
    return render_template('rapports/tableau_bord.html',
                           f=f,
                           r=rapport,
                           periodes=[('7j', '7 jours'), ('30j', '30 jours'), ('90j', '90 jours'), ('1a', '12 mois')],
                           departements=Departement.query.filter_by(actif=True).order_by(Departement.nom).all(),
                           pdvs=PointDeVente.query.filter_by(actif=True).order_by(PointDeVente.nom).all(),
                           agents=sorted([u for u in Utilisateur.query.filter_by(actif=True).all()
                                          if u.has_permission('tickets.modifier') or u.has_permission('tickets.cloturer')],
                                         key=lambda u: (u.nom_complet or '').upper()),
                           types=reporting.TYPES, priorites=reporting.PRIORITES,
                           export_args=reporting.query_args(f),
                           date_debut_iso=f['debut'].strftime('%Y-%m-%d'),
                           date_fin_iso=(f['fin'] - timedelta(days=1)).strftime('%Y-%m-%d'))


def _agents_list():
    """Agents = utilisateurs actifs autorisés à traiter des tickets, ou à qui des tickets ont été assignés."""
    assigned = {row[0] for row in db.session.query(Ticket.assigne_a_id).filter(Ticket.assigne_a_id.isnot(None)).distinct()}
    return [u for u in Utilisateur.query.filter_by(actif=True).all()
            if u.id in assigned or u.has_permission('tickets.modifier') or u.has_permission('tickets.cloturer')]


PERIODES_AGENTS = [('7j', '7 jours'), ('30j', '30 jours'), ('90j', '90 jours'), ('1a', '12 mois')]


@rapports_bp.route('/performance-agents')
@login_required
@permission_required('rapports_performance.voir')
def performance_agents():
    """Classement simple des agents : qui résout combien de tickets, à quelle vitesse"""
    f = reporting.parse_filters({'periode': request.args.get('periode', '30j')})
    rows, team = reporting.agents_overview(f, _agents_list())
    return render_template('rapports/performance_agents.html', f=f, rows=rows, team=team, periodes=PERIODES_AGENTS)


@rapports_bp.route('/performance-agents/<string:agent_id>/tickets')
@login_required
@permission_required('rapports_performance.voir')
def agent_tickets(agent_id):
    """Fiche d'un agent : ses chiffres, ses tickets à traiter, ses tickets résolus"""
    agent = Utilisateur.query.get_or_404(agent_id)
    f = reporting.parse_filters({'periode': request.args.get('periode', '30j')})
    numbers, team, to_handle, done = reporting.agent_detail(f, agent)
    return render_template('rapports/agent_tickets.html', f=f, agent=agent, n=numbers, team=team,
                           to_handle=to_handle, done=done, periodes=PERIODES_AGENTS)


@rapports_bp.route('/satisfaction-client')
@login_required
@permission_required('rapports_globaux.voir')
def satisfaction_client():
    """La satisfaction est désormais intégrée au rapport global."""
    return redirect(url_for('rapports.tableau_bord', **request.args) + '#satisfaction')


@rapports_bp.route('/export/csv')
@login_required
@permission_required('rapports_globaux.voir')
def export_csv():
    """Exporte en CSV les tickets créés sur la période, avec les mêmes filtres que le rapport"""
    if not current_user.has_permission('rapports_globaux.exporter'):
        flash("Vous n'avez pas la permission d'exporter les rapports.", 'danger')
        return redirect(url_for('rapports.tableau_bord'))
    for key in ('date_debut', 'date_fin'):
        if request.args.get(key) and not _parse_iso(request.args.get(key)):
            flash('Date invalide : utilisez le format AAAA-MM-JJ.', 'danger')
            return redirect(url_for('rapports.tableau_bord'))
    f = reporting.parse_filters(request.args)
    rows = reporting.export_rows(f)

    def d(value):
        return value.strftime('%d/%m/%Y %H:%M') if value else ''

    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(['Numéro', 'Titre', 'Type', 'Priorité', 'Statut', 'Créateur', 'Assigné à', 'Département',
                     'Catégorie', 'Point de vente', 'Date création', 'Échéance SLA', 'Date résolution',
                     '1ère réponse (min)', 'Résolution (min)', 'SLA respecté', 'Satisfaction'])
    for t in rows:
        writer.writerow([csv_safe(v) for v in [
            t['numero'], t['titre'], t['type'], t['priorite'], t['statut'], t['createur'], t['assigne'],
            t['departement'], t['categorie'], t['pdv'], d(t['creation']), d(t['echeance']), d(t['resolution']),
            t['t_reponse'] if t['t_reponse'] is not None else '', t['t_resolution'] if t['t_resolution'] is not None else '',
            '' if t['sla'] is None else ('oui' if t['sla'] else 'non'), t['satisfaction'] or '']])

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
