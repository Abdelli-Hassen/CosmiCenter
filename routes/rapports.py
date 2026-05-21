from flask import Blueprint, render_template, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Ticket, Utilisateur, Departement, CategorieTicket, Statistique
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from functools import wraps
import io
import csv

rapports_bp = Blueprint('rapports', __name__)


def manager_required(f):
    """Décorateur pour les gestionnaires et administrateurs"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.has_permission('rapports.voir'):
            flash('Accès non autorisé.', 'danger')
            return redirect(url_for('tickets.tableau_bord'))
        return f(*args, **kwargs)
    return decorated_function


@rapports_bp.route('/')
@login_required
@manager_required
def tableau_bord():
    """Tableau de bord principal des rapports"""
    # Période par défaut: 30 derniers jours
    date_fin = datetime.now()
    date_debut = date_fin - timedelta(days=30)
    
    # Paramètres de période
    periode = request.args.get('periode', '30j')
    if periode == '7j':
        date_debut = date_fin - timedelta(days=7)
    elif periode == '30j':
        date_debut = date_fin - timedelta(days=30)
    elif periode == '90j':
        date_debut = date_fin - timedelta(days=90)
    elif periode == '1a':
        date_debut = date_fin - timedelta(days=365)
    
    # Statistiques globales
    stats_globales = {
        'total_tickets': Ticket.query.filter(
            Ticket.date_creation >= date_debut
        ).count(),
        'tickets_ouverts': Ticket.query.filter(
            Ticket.statut.in_(['nouveau', 'en_cours', 'en_attente'])
        ).count(),
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
    
    # Tickets par statut
    tickets_par_statut = db.session.query(
        Ticket.statut,
        func.count(Ticket.id)
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(Ticket.statut).all()
    
    # Tickets par priorité
    tickets_par_priorite = db.session.query(
        Ticket.priorite,
        func.count(Ticket.id)
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(Ticket.priorite).all()
    
    # Tickets par type
    tickets_par_type = db.session.query(
        Ticket.type_ticket,
        func.count(Ticket.id)
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(Ticket.type_ticket).all()
    
    # Tickets par département
    tickets_par_departement = db.session.query(
        Departement.nom,
        func.count(Ticket.id)
    ).join(
        CategorieTicket, Ticket.categorie_id == CategorieTicket.id
    ).join(
        Departement, CategorieTicket.departement_id == Departement.id
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(Departement.nom).all()
    
    # Évolution des tickets (par jour)
    evolution_tickets = db.session.query(
        func.date(Ticket.date_creation).label('date'),
        func.count(Ticket.id).label('count')
    ).filter(
        Ticket.date_creation >= date_debut
    ).group_by(func.date(Ticket.date_creation)).all()
    
    # Temps moyen de résolution
    temps_moyen_resolution = db.session.query(
        func.avg(Ticket.temps_resolution_minutes)
    ).filter(
        Ticket.date_resolution >= date_debut,
        Ticket.temps_resolution_minutes.isnot(None)
    ).scalar() or 0
    
    # Temps moyen de première réponse
    temps_moyen_premiere_reponse = db.session.query(
        func.avg(Ticket.temps_premiere_reponse_minutes)
    ).filter(
        Ticket.date_premiere_reponse >= date_debut,
        Ticket.temps_premiere_reponse_minutes.isnot(None)
    ).scalar() or 0
    
    # Taux de satisfaction
    satisfaction_moyenne = db.session.query(
        func.avg(Ticket.satisfaction)
    ).filter(
        Ticket.satisfaction.isnot(None),
        Ticket.date_fermeture >= date_debut
    ).scalar() or 0
    
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
    
    # SLA - Taux de respect
    tickets_avec_sla = Ticket.query.filter(
        Ticket.date_creation >= date_debut,
        Ticket.sla_respecte.isnot(None)
    ).count()
    
    tickets_sla_respecte = Ticket.query.filter(
        Ticket.date_creation >= date_debut,
        Ticket.sla_respecte == True
    ).count()
    
    taux_sla = (tickets_sla_respecte / tickets_avec_sla * 100) if tickets_avec_sla > 0 else 0
    
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


@rapports_bp.route('/performance-agents')
@login_required
@manager_required
def performance_agents():
    """Rapport de performance des agents"""
    # Période
    periode = request.args.get('periode', '30j')
    date_fin = datetime.now()
    
    if periode == '7j':
        date_debut = date_fin - timedelta(days=7)
    elif periode == '30j':
        date_debut = date_fin - timedelta(days=30)
    elif periode == '90j':
        date_debut = date_fin - timedelta(days=90)
    else:
        date_debut = date_fin - timedelta(days=365)
    
    # Statistiques par agent
    agents = Utilisateur.query.filter_by(actif=True).all()
    
    stats_agents = []
    for agent in agents:
        tickets_assignes = Ticket.query.filter(
            Ticket.assigne_a_id == agent.id,
            Ticket.date_creation >= date_debut
        ).all()
        
        tickets_resolus = [t for t in tickets_assignes if t.statut == 'resolu']
        tickets_en_cours = [t for t in tickets_assignes if t.statut in ['nouveau', 'en_cours', 'en_attente']]
        
        # Temps moyen de résolution pour cet agent
        temps_resolution = [t.temps_resolution_minutes for t in tickets_resolus 
                          if t.temps_resolution_minutes is not None]
        temps_moyen = sum(temps_resolution) / len(temps_resolution) if temps_resolution else 0
        
        # Satisfaction moyenne
        satisfactions = [t.satisfaction for t in tickets_resolus if t.satisfaction is not None]
        satisfaction_moyenne = sum(satisfactions) / len(satisfactions) if satisfactions else 0
        
        stats_agents.append({
            'agent': agent,
            'total_tickets': len(tickets_assignes),
            'tickets_resolus': len(tickets_resolus),
            'tickets_en_cours': len(tickets_en_cours),
            'temps_moyen_resolution': temps_moyen,
            'satisfaction_moyenne': satisfaction_moyenne,
            'taux_resolution': (len(tickets_resolus) / len(tickets_assignes) * 100) 
                              if tickets_assignes else 0
        })
    
    # Trier par nombre de tickets résolus
    stats_agents.sort(key=lambda x: x['tickets_resolus'], reverse=True)
    
    return render_template('rapports/performance_agents.html',
                         stats_agents=stats_agents,
                         periode=periode,
                         date_debut=date_debut,
                         date_fin=date_fin)


@rapports_bp.route('/satisfaction-client')
@login_required
@manager_required
def satisfaction_client():
    """Rapport de satisfaction client"""
    periode = request.args.get('periode', '30j')
    date_fin = datetime.now()
    
    if periode == '7j':
        date_debut = date_fin - timedelta(days=7)
    elif periode == '30j':
        date_debut = date_fin - timedelta(days=30)
    elif periode == '90j':
        date_debut = date_fin - timedelta(days=90)
    else:
        date_debut = date_fin - timedelta(days=365)
    
    # Tickets avec évaluation
    tickets_evalues = Ticket.query.filter(
        Ticket.satisfaction.isnot(None),
        Ticket.date_fermeture >= date_debut
    ).all()
    
    # Distribution des notes
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for ticket in tickets_evalues:
        distribution[ticket.satisfaction] = distribution.get(ticket.satisfaction, 0) + 1
    
    # Satisfaction moyenne globale
    satisfactions = [t.satisfaction for t in tickets_evalues]
    satisfaction_moyenne = sum(satisfactions) / len(satisfactions) if satisfactions else 0
    
    # Satisfaction par département
    satisfaction_par_dept = {}
    departements = Departement.query.filter_by(actif=True).all()
    
    for dept in departements:
        tickets_dept = [t for t in tickets_evalues 
                       if t.categorie and t.categorie.departement_id == dept.id]
        if tickets_dept:
            satisfactions_dept = [t.satisfaction for t in tickets_dept]
            satisfaction_par_dept[dept.nom] = sum(satisfactions_dept) / len(satisfactions_dept)
    
    # Commentaires récents (positifs et négatifs)
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
@manager_required
def export_csv():
    """Exporter les tickets en CSV"""
    # Paramètres
    date_debut = request.args.get('date_debut')
    date_fin = request.args.get('date_fin')
    
    query = Ticket.query
    
    if date_debut:
        query = query.filter(Ticket.date_creation >= datetime.fromisoformat(date_debut))
    if date_fin:
        query = query.filter(Ticket.date_creation <= datetime.fromisoformat(date_fin))
    
    tickets = query.order_by(Ticket.date_creation.desc()).all()
    
    # Créer le CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # En-têtes
    writer.writerow([
        'Numéro', 'Titre', 'Type', 'Priorité', 'Statut',
        'Créateur', 'Assigné à', 'Département', 'Catégorie',
        'Date création', 'Date résolution', 'Satisfaction'
    ])
    
    # Données
    for ticket in tickets:
        writer.writerow([
            ticket.numero,
            ticket.titre,
            ticket.type_ticket,
            ticket.priorite,
            ticket.statut,
            ticket.createur.nom_complet if ticket.createur else '',
            ticket.assigne_a.nom_complet if ticket.assigne_a else '',
            ticket.categorie.departement.nom if ticket.categorie else '',
            ticket.categorie.nom if ticket.categorie else '',
            ticket.date_creation.strftime('%d/%m/%Y %H:%M'),
            ticket.date_resolution.strftime('%d/%m/%Y %H:%M') if ticket.date_resolution else '',
            ticket.satisfaction or ''
        ])
    
    # Préparer la réponse
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'tickets_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )


@rapports_bp.route('/api/stats')
@login_required
@manager_required
def api_stats():
    """API pour obtenir des statistiques en JSON"""
    type_stat = request.args.get('type', 'general')
    periode = request.args.get('periode', '30j')
    
    date_fin = datetime.now()
    if periode == '7j':
        date_debut = date_fin - timedelta(days=7)
    elif periode == '30j':
        date_debut = date_fin - timedelta(days=30)
    elif periode == '90j':
        date_debut = date_fin - timedelta(days=90)
    else:
        date_debut = date_fin - timedelta(days=365)
    
    if type_stat == 'evolution':
        # Évolution quotidienne
        evolution = db.session.query(
            func.date(Ticket.date_creation).label('date'),
            func.count(Ticket.id).label('count')
        ).filter(
            Ticket.date_creation >= date_debut
        ).group_by(func.date(Ticket.date_creation)).all()
        
        return jsonify({
            'dates': [str(e.date) for e in evolution],
            'counts': [e.count for e in evolution]
        })
    
    elif type_stat == 'statuts':
        # Répartition par statut
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
