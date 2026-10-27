"""
Moteur des rapports globaux : toutes les agrégations viennent de la table `tickets` (et des tables liées),
sans aucune nouvelle table. Les durées sont stockées en minutes.

Vocabulaire :
- « créés »    : tickets dont la date de création est dans la période ;
- « résolus »  : tickets résolus/fermés dont la date de résolution (à défaut de fermeture) est dans la période ;
- « backlog »  : tickets actuellement ouverts (indépendamment de la période, mêmes filtres) ;
- « en retard »: tickets ouverts dont l'échéance SLA est dépassée.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import aliased

from models import db, Ticket, Utilisateur, Departement, PointDeVente, CategorieTicket, HistoriqueTicket

STATUTS_OUVERTS = ['nouveau', 'ouvert', 'en_cours', 'en_attente']
STATUTS_RESOLUS = ['resolu', 'ferme']
PRIORITES = ['critique', 'urgente', 'haute', 'moyenne', 'basse']
TYPES = ['incident', 'demande', 'besoin', 'plainte', 'tache']
PERIODES = {'7j': 7, '30j': 30, '90j': 90, '1a': 365}
JOURS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']


# ─── Utilitaires ────────────────────────────────────────────────────────────
def fmt_minutes(m):
    """Durée lisible : « 45 min », « 6,5 h », « 2,3 j » ; « — » sans donnée."""
    if m is None:
        return '—'
    m = float(m)
    if m < 60:
        return f'{round(m)} min'
    h = m / 60
    if h < 48:
        return f'{h:.1f} h'.replace('.', ',')
    return f'{h / 24:.1f} j'.replace('.', ',')


def _avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else None


def _pct(part, total):
    return (part / total * 100) if total else None


def _delta(cur, prev, higher_is_better=True, points=False):
    """Évolution par rapport à la période précédente : (texte, classe css) ou None."""
    if cur is None or prev is None:
        return None
    if points:
        diff = cur - prev
        if abs(diff) < 0.05:
            return ('= stable', 'neutral')
        txt = f"{'▲' if diff > 0 else '▼'} {abs(diff):.1f} pt".replace('.', ',')
    else:
        if prev == 0:
            return None
        diff = (cur - prev) / prev * 100
        if abs(diff) < 0.5:
            return ('= stable', 'neutral')
        txt = f"{'▲' if diff > 0 else '▼'} {abs(diff):.0f} %"
    good = (diff > 0) == higher_is_better
    return (txt + ' vs période préc.', 'good' if good else 'bad')


def parse_filters(args, now=None):
    """Lit ?periode=, ?date_debut=, ?date_fin= et les filtres ; retourne un dict validé."""
    now = now or datetime.utcnow()
    f = {'periode': args.get('periode') or '30j'}
    d_debut, d_fin = args.get('date_debut'), args.get('date_fin')

    def _d(v):
        try:
            return datetime.strptime(v[:10], '%Y-%m-%d')
        except (TypeError, ValueError):
            return None

    start, end = _d(d_debut), _d(d_fin)
    if start or end:
        f['periode'] = 'perso'
        end = end or now
        start = start or end - timedelta(days=30)
        if start > end:
            start, end = end, start
        f['debut'] = start
        f['fin'] = end.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    else:
        if f['periode'] not in PERIODES:
            f['periode'] = '30j'
        f['fin'] = now
        f['debut'] = now - timedelta(days=PERIODES[f['periode']])
    # Durée maximale analysée : 5 ans (protège la mémoire du serveur)
    if (f['fin'] - f['debut']).days > 1830:
        f['debut'] = f['fin'] - timedelta(days=1830)

    f['departement_id'] = args.get('departement') or None
    f['pdv_id'] = args.get('pdv') or None
    f['type_ticket'] = args.get('type') if args.get('type') in TYPES else None
    f['priorite'] = args.get('priorite') if args.get('priorite') in PRIORITES else None
    f['agent_id'] = args.get('agent') or None
    f['now'] = now
    return f


def query_args(f):
    """Filtres actifs sous forme de paramètres d'URL (pour les liens d'export)."""
    out = {}
    if f['periode'] == 'perso':
        out['date_debut'] = f['debut'].strftime('%Y-%m-%d')
        out['date_fin'] = (f['fin'] - timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        out['periode'] = f['periode']
    for key, val in (('departement', f['departement_id']), ('pdv', f['pdv_id']), ('type', f['type_ticket']),
                     ('priorite', f['priorite']), ('agent', f['agent_id'])):
        if val:
            out[key] = val
    return out


# ─── Requêtes ───────────────────────────────────────────────────────────────
def _base(f):
    """Requête de base : colonnes utiles + filtres communs (département, PDV, type, priorité, agent)."""
    creator = aliased(Utilisateur)
    pdv_expr = func.coalesce(Ticket.pdv_id, creator.pdv_id)
    resolution_date = func.coalesce(Ticket.date_resolution, Ticket.date_fermeture)
    q = (db.session.query(
        Ticket.id, Ticket.numero, Ticket.titre, Ticket.type_ticket, Ticket.priorite, Ticket.statut,
        Ticket.departement_id, Ticket.categorie_id, Ticket.assigne_a_id, Ticket.createur_id,
        Ticket.date_creation, Ticket.date_echeance, Ticket.sla_respecte,
        Ticket.temps_premiere_reponse_minutes.label('t_reponse'),
        Ticket.temps_resolution_minutes.label('t_resolution'),
        Ticket.satisfaction, Ticket.commentaire_satisfaction,
        pdv_expr.label('pdv'), resolution_date.label('date_resol'))
        .select_from(Ticket).outerjoin(creator, creator.id == Ticket.createur_id))
    if f['departement_id']:
        q = q.filter(Ticket.departement_id == f['departement_id'])
    if f['pdv_id']:
        q = q.filter(pdv_expr == f['pdv_id'])
    if f['type_ticket']:
        q = q.filter(Ticket.type_ticket == f['type_ticket'])
    if f['priorite']:
        q = q.filter(Ticket.priorite == f['priorite'])
    if f['agent_id']:
        q = q.filter(Ticket.assigne_a_id == f['agent_id'])
    return q, resolution_date


def fetch(f, debut=None, fin=None):
    """(créés, résolus) dans [debut, fin[ ."""
    debut, fin = debut or f['debut'], fin or f['fin']
    q, resolution_date = _base(f)
    created = q.filter(Ticket.date_creation >= debut, Ticket.date_creation < fin).all()
    resolved = (_base(f)[0].filter(Ticket.statut.in_(STATUTS_RESOLUS), resolution_date >= debut, resolution_date < fin).all())
    return created, resolved


def fetch_open(f):
    return _base(f)[0].filter(Ticket.statut.in_(STATUTS_OUVERTS)).all()


def export_rows(f):
    """Tickets créés dans la période, avec leurs libellés, pour l'export CSV."""
    created, _ = fetch(f)
    depts = {d.id: d.nom for d in Departement.query.all()}
    users = {u.id: u.nom_complet for u in Utilisateur.query.all()}
    cats = {c.id: c.nom for c in CategorieTicket.query.all()}
    pdvs = {p.id: p.nom for p in PointDeVente.query.all()}
    return [{
        'numero': t.numero, 'titre': t.titre, 'type': t.type_ticket, 'priorite': t.priorite, 'statut': t.statut,
        'createur': users.get(t.createur_id, ''), 'assigne': users.get(t.assigne_a_id, ''),
        'departement': depts.get(t.departement_id, ''), 'categorie': cats.get(t.categorie_id, ''),
        'pdv': pdvs.get(t.pdv, ''), 'creation': t.date_creation, 'echeance': t.date_echeance,
        'resolution': t.date_resol, 't_reponse': t.t_reponse, 't_resolution': t.t_resolution,
        'sla': t.sla_respecte, 'satisfaction': t.satisfaction,
    } for t in sorted(created, key=lambda r: r.date_creation, reverse=True)]


# ─── Performance des agents ─────────────────────────────────────────────────
def _agent_numbers(resolved, opened, now):
    """Chiffres simples d'un agent : résolus, en cours, en retard, délai moyen, respect du SLA, satisfaction."""
    sla_set = [t for t in resolved if t.sla_respecte is not None]
    overdue = sum(1 for t in opened if t.date_echeance and t.date_echeance < now)
    n = {
        'resolved': len(resolved),
        'open': len(opened),
        'overdue': overdue,
        'res_avg_min': _avg([t.t_resolution for t in resolved]),
        'sla': _pct(sum(1 for t in sla_set if t.sla_respecte), len(sla_set)),
        'csat': _avg([t.satisfaction for t in resolved if t.satisfaction is not None]),
    }
    n['res_avg'] = fmt_minutes(n['res_avg_min'])
    # « Situation » : règle volontairement simple, expliquée sur la page
    if not resolved and not opened:
        n['situation'] = 'inactif'
    elif overdue >= 3 or (n['sla'] is not None and n['sla'] < 60):
        n['situation'] = 'attention'
    elif overdue >= 1 or (n['sla'] is not None and n['sla'] < 80):
        n['situation'] = 'surveiller'
    else:
        n['situation'] = 'ok'
    return n


def agents_overview(f, agents):
    """Classement des agents (résolus sur la période, tickets en cours aujourd'hui) + chiffres de l'équipe."""
    now = f['now']
    f = dict(f, agent_id=None)
    _, resolved = fetch(f)
    opened = fetch_open(f)
    rows = []
    for a in agents:
        r = [t for t in resolved if t.assigne_a_id == a.id]
        o = [t for t in opened if t.assigne_a_id == a.id]
        rows.append({'agent': a, **_agent_numbers(r, o, now)})
    rows.sort(key=lambda x: (-x['resolved'], -x['open'], (x['agent'].nom_complet or '').upper()))
    for i, row in enumerate(rows, 1):
        row['rank'] = i if row['resolved'] else None
    team = _agent_numbers(resolved, opened, now)
    team['unassigned'] = sum(1 for t in opened if not t.assigne_a_id)
    team['active_agents'] = sum(1 for r in rows if r['situation'] != 'inactif')
    team['res_avg'] = fmt_minutes(team['res_avg_min'])
    return rows, team


def agent_detail(f, agent):
    """Détail d'un agent : chiffres, comparaison avec l'équipe, tickets à traiter, tickets résolus."""
    now = f['now']
    team_f = dict(f, agent_id=None)
    _, team_resolved = fetch(team_f)
    team = _agent_numbers(team_resolved, [], now)
    mine_f = dict(f, agent_id=agent.id)
    _, resolved = fetch(mine_f)
    opened = fetch_open(mine_f)
    numbers = _agent_numbers(resolved, opened, now)

    depts = {d.id: d.nom for d in Departement.query.all()}

    def row(t):
        late = bool(t.date_echeance and t.date_echeance < now and t.statut in STATUTS_OUVERTS)
        return {
            'id': t.id, 'numero': t.numero, 'titre': t.titre, 'priorite': t.priorite, 'statut': t.statut,
            'departement': depts.get(t.departement_id, '—'),
            'created': t.date_creation, 'due': t.date_echeance, 'resolved_at': t.date_resol,
            'duree': fmt_minutes(t.t_resolution), 'sla': t.sla_respecte, 'note': t.satisfaction,
            'late': late,
            'late_by': fmt_minutes((now - t.date_echeance).total_seconds() / 60) if late else None,
        }
    to_handle = sorted((row(t) for t in opened), key=lambda x: (not x['late'], x['due'] or datetime.max))
    done = sorted((row(t) for t in resolved), key=lambda x: x['resolved_at'] or datetime.min, reverse=True)
    return numbers, team, to_handle, done


# ─── Calcul principal ───────────────────────────────────────────────────────
def _summary(created, resolved, opened, now):
    res_times = [t.t_resolution for t in resolved if t.t_resolution is not None]
    sla_set = [t for t in resolved if t.sla_respecte is not None]
    rated = [t.satisfaction for t in resolved if t.satisfaction is not None]
    done_from_created = [t for t in created if t.statut in STATUTS_RESOLUS]
    return {
        'created': len(created),
        'resolved': len(resolved),
        'backlog': len(opened),
        'overdue': sum(1 for t in opened if t.date_echeance and t.date_echeance < now),
        'unassigned': sum(1 for t in opened if not t.assigne_a_id),
        'resolution_rate': _pct(len(done_from_created), len([t for t in created if t.statut != 'annule'])),
        'first_response': _avg([t.t_reponse for t in created]),
        'resolution_avg': _avg(res_times),
        'resolution_median': median(res_times) if res_times else None,
        'sla': _pct(sum(1 for t in sla_set if t.sla_respecte), len(sla_set)),
        'sla_n': len(sla_set),
        'csat': _avg(rated),
        'csat_n': len(rated),
    }


def build_report(f):
    now = f['now']
    created, resolved = fetch(f)
    opened = fetch_open(f)
    span = f['fin'] - f['debut']
    prev_created, prev_resolved = fetch(f, f['debut'] - span, f['debut'])
    cur = _summary(created, resolved, opened, now)
    prev = _summary(prev_created, prev_resolved, [], now)

    # Lookups libellés
    depts = {d.id: d for d in Departement.query.all()}
    users = {u.id: u for u in Utilisateur.query.all()}
    cats = {c.id: c for c in CategorieTicket.query.all()}
    pdvs = {p.id: p for p in PointDeVente.query.all()}

    # Réouvertures survenues dans la période, pour les tickets correspondant aux filtres
    filtered_ids = _base(f)[0].with_entities(Ticket.id).subquery()
    reopened = db.session.query(func.count(HistoriqueTicket.id)).filter(
        HistoriqueTicket.action.ilike('Réouverture%'),
        HistoriqueTicket.date_creation >= f['debut'], HistoriqueTicket.date_creation < f['fin'],
        HistoriqueTicket.ticket_id.in_(db.session.query(filtered_ids.c.id))).scalar()

    kpis = [
        {'key': 'created', 'label': 'Tickets créés', 'value': str(cur['created']), 'color': '#3b82f6', 'icon': 'file',
         'sub': f"{cur['resolved']} résolus sur la période",
         'delta': _delta(cur['created'], prev['created'], higher_is_better=False)},
        {'key': 'resolved', 'label': 'Tickets résolus', 'value': str(cur['resolved']), 'color': '#10b981', 'icon': 'check',
         'sub': 'résolus ou fermés',
         'delta': _delta(cur['resolved'], prev['resolved'])},
        {'key': 'backlog', 'label': 'En attente de traitement', 'value': str(cur['backlog']), 'color': '#f59e0b', 'icon': 'inbox',
         'sub': f"dont {cur['unassigned']} non assigné(s)", 'delta': None},
        {'key': 'overdue', 'label': 'En retard (SLA)', 'value': str(cur['overdue']), 'color': '#ef4444', 'icon': 'alert',
         'sub': 'ouverts, échéance dépassée', 'delta': None, 'bad_if_positive': True},
        {'key': 'resolution_rate', 'label': 'Taux de résolution',
         'value': f"{cur['resolution_rate']:.0f} %" if cur['resolution_rate'] is not None else '—', 'color': '#06b6d4', 'icon': 'target',
         'sub': 'des tickets créés sont résolus', 'delta': _delta(cur['resolution_rate'], prev['resolution_rate'], points=True)},
        {'key': 'sla', 'label': 'Conformité SLA',
         'value': f"{cur['sla']:.1f} %".replace('.', ',') if cur['sla'] is not None else '—', 'color': '#10b981', 'icon': 'shield',
         'sub': f"{cur['sla_n']} ticket(s) mesuré(s) · objectif 90 %",
         'delta': _delta(cur['sla'], prev['sla'], points=True), 'tip': 'conformite'},
        {'key': 'first_response', 'label': '1ère réponse (moy.)', 'value': fmt_minutes(cur['first_response']), 'color': '#8b5cf6', 'icon': 'clock',
         'sub': 'délai avant la 1ère prise en charge',
         'delta': _delta(cur['first_response'], prev['first_response'], higher_is_better=False)},
        {'key': 'resolution', 'label': 'Résolution (moy.)', 'value': fmt_minutes(cur['resolution_avg']), 'color': '#f59e0b', 'icon': 'clock',
         'sub': f"médiane : {fmt_minutes(cur['resolution_median'])}",
         'delta': _delta(cur['resolution_avg'], prev['resolution_avg'], higher_is_better=False)},
        {'key': 'csat', 'label': 'Satisfaction',
         'value': f"{cur['csat']:.1f} / 5".replace('.', ',') if cur['csat'] is not None else '—', 'color': '#ec4899', 'icon': 'star',
         'sub': f"{cur['csat_n']} évaluation(s)", 'delta': _delta(cur['csat'], prev['csat'], points=True)},
        {'key': 'reopened', 'label': 'Réouvertures', 'value': str(reopened or 0), 'color': '#64748b', 'icon': 'redo',
         'sub': 'tickets rouverts sur la période', 'delta': None, 'bad_if_positive': True},
    ]

    # ── Évolution (jour ou semaine) ──
    days = max((f['fin'] - f['debut']).days, 1)
    step = 1 if days <= 92 else 7
    start_day = f['debut'].replace(hour=0, minute=0, second=0, microsecond=0)
    buckets = []
    d = start_day
    while d < f['fin']:
        buckets.append(d)
        d += timedelta(days=step)
    idx = lambda dt: min(max(int((dt - start_day).days // step), 0), len(buckets) - 1)
    s_created, s_resolved = [0] * len(buckets), [0] * len(buckets)
    for t in created:
        s_created[idx(t.date_creation)] += 1
    for t in resolved:
        s_resolved[idx(t.date_resol)] += 1
    series = {
        'labels': [b.strftime('%d/%m') for b in buckets],
        'created': s_created, 'resolved': s_resolved,
        'step': step,
    }

    # ── Répartitions ──
    by_status = Counter(t.statut for t in created)
    by_type = Counter(t.type_ticket or 'autre' for t in created)
    by_prio = Counter(t.priorite for t in created)
    backlog_prio = Counter(t.priorite for t in opened)

    ages = Counter()
    for t in opened:
        age = (now - t.date_creation).total_seconds() / 86400
        ages['< 1 jour' if age < 1 else '1 à 3 jours' if age < 3 else '3 à 7 jours' if age < 7 else '7 à 14 jours' if age < 14 else '> 14 jours'] += 1
    backlog_age = [(k, ages.get(k, 0)) for k in ('< 1 jour', '1 à 3 jours', '3 à 7 jours', '7 à 14 jours', '> 14 jours')]

    # ── Départements ──
    dept_ids = {t.departement_id for t in created + resolved + opened}
    dept_rows = []
    for did in dept_ids:
        c = [t for t in created if t.departement_id == did]
        r = [t for t in resolved if t.departement_id == did]
        o = [t for t in opened if t.departement_id == did]
        sla_set = [t for t in r if t.sla_respecte is not None]
        rated = [t.satisfaction for t in r if t.satisfaction is not None]
        dept_rows.append({
            'nom': depts[did].nom if did in depts else 'Sans département',
            'couleur': getattr(depts.get(did), 'couleur', None) or '#64748b',
            'created': len(c), 'resolved': len(r), 'open': len(o),
            'overdue': sum(1 for t in o if t.date_echeance and t.date_echeance < now),
            'res_avg': fmt_minutes(_avg([t.t_resolution for t in r])),
            'sla': _pct(sum(1 for t in sla_set if t.sla_respecte), len(sla_set)),
            'csat': _avg(rated),
        })
    dept_rows.sort(key=lambda x: (-x['created'], -x['open'], x['nom']))

    # ── Catégories (top 10) ──
    cat_rows = []
    for cid in {t.categorie_id for t in created}:
        c = [t for t in created if t.categorie_id == cid]
        r = [t for t in resolved if t.categorie_id == cid]
        cat_rows.append({
            'nom': cats[cid].nom if cid in cats else 'Sans catégorie',
            'couleur': getattr(cats.get(cid), 'couleur', None) or '#64748b',
            'count': len(c), 'res_avg': fmt_minutes(_avg([t.t_resolution for t in r])),
        })
    cat_rows.sort(key=lambda x: -x['count'])

    # ── Points de vente (top 10) ──
    pdv_rows = []
    for pid in {t.pdv for t in created + opened}:
        c = [t for t in created if t.pdv == pid]
        o = [t for t in opened if t.pdv == pid]
        pdv_rows.append({
            'nom': pdvs[pid].nom if pid in pdvs else 'Siège / sans point de vente',
            'couleur': getattr(pdvs.get(pid), 'couleur', None) or '#64748b',
            'created': len(c), 'open': len(o),
            'overdue': sum(1 for t in o if t.date_echeance and t.date_echeance < now),
        })
    pdv_rows.sort(key=lambda x: (-x['created'], -x['open'], x['nom']))

    # ── Agents ──
    agent_rows = []
    for aid in {t.assigne_a_id for t in created + resolved + opened if t.assigne_a_id}:
        c = [t for t in created if t.assigne_a_id == aid]
        r = [t for t in resolved if t.assigne_a_id == aid]
        o = [t for t in opened if t.assigne_a_id == aid]
        u = users.get(aid)
        agent_rows.append({
            'nom': u.nom_complet if u else '—', 'assigned': len(c), 'resolved': len(r), 'open': len(o),
            'res_avg': fmt_minutes(_avg([t.t_resolution for t in r])),
            'csat': _avg([t.satisfaction for t in r if t.satisfaction is not None]),
        })
    agent_rows.sort(key=lambda x: (-x['resolved'], -x['assigned'], x['nom']))

    # ── Carte de chaleur jour × heure (création) ──
    heat = [[0] * 24 for _ in range(7)]
    for t in created:
        heat[t.date_creation.weekday()][t.date_creation.hour] += 1
    heat_max = max((v for row in heat for v in row), default=0)

    # ── Tickets en retard (les plus anciens d'abord) ──
    overdue = sorted([t for t in opened if t.date_echeance and t.date_echeance < now], key=lambda t: t.date_echeance)[:10]
    overdue_rows = [{
        'id': t.id, 'numero': t.numero, 'titre': t.titre, 'priorite': t.priorite,
        'departement': depts[t.departement_id].nom if t.departement_id in depts else '—',
        'assigne': users[t.assigne_a_id].nom_complet if t.assigne_a_id in users else 'Non assigné',
        'retard': fmt_minutes((now - t.date_echeance).total_seconds() / 60),
    } for t in overdue]

    # ── Satisfaction ──
    rated = [t for t in resolved if t.satisfaction is not None]
    dist = Counter(t.satisfaction for t in rated)
    comment = lambda t: {'id': t.id, 'numero': t.numero, 'titre': t.titre, 'note': t.satisfaction, 'texte': t.commentaire_satisfaction}
    good_comments = [comment(t) for t in rated if t.satisfaction >= 4 and t.commentaire_satisfaction][:5]
    bad_comments = [comment(t) for t in rated if t.satisfaction <= 2 and t.commentaire_satisfaction][:5]

    return {
        'kpis': kpis, 'summary': cur, 'previous': prev, 'series': series,
        'by_status': dict(by_status), 'by_type': dict(by_type), 'by_prio': dict(by_prio),
        'backlog_prio': dict(backlog_prio), 'backlog_age': backlog_age,
        'departements': dept_rows, 'categories': cat_rows[:10], 'categories_total': len(cat_rows),
        'pdvs': pdv_rows[:10], 'pdvs_total': len(pdv_rows),
        'agents': agent_rows[:10], 'agents_total': len(agent_rows),
        'heat': heat, 'heat_max': heat_max, 'jours': JOURS,
        'overdue_rows': overdue_rows,
        'satisfaction': {'dist': {i: dist.get(i, 0) for i in range(1, 6)}, 'n': len(rated), 'avg': cur['csat'],
                         'good': good_comments, 'bad': bad_comments},
        'days': days,
    }
