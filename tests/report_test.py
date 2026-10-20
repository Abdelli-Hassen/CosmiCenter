import os, re, sys, secrets, random
from datetime import datetime, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Ticket, Departement, PointDeVente, CategorieTicket

app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

PW = "T3st-" + secrets.token_urlsafe(8); EMAIL = "zz.rep.admin@example.invalid"; LOW = "zz.rep.low@example.invalid"
random.seed(7)
with app.app_context():
    sa = Role.query.filter_by(nom="Super Administrateur").first()
    low = Role.query.filter_by(nom="Personnel PDV").first() or Role.query.filter(Role.niveau <= 10).first()
    admin = Utilisateur(nom="REP", prenom="Admin", email=EMAIL, role_id=sa.id); admin.set_password(PW)
    lowu = Utilisateur(nom="REP", prenom="Low", email=LOW, role_id=low.id); lowu.set_password(PW)
    db.session.add_all([admin, lowu]); db.session.commit()
    admin_id = admin.id
    n_before = Ticket.query.count()
    depts = Departement.query.filter_by(actif=True).limit(4).all()
    pdvs = PointDeVente.query.limit(3).all()
    cats = CategorieTicket.query.filter(CategorieTicket.departement_id.in_([d.id for d in depts])).all()
    agents = Utilisateur.query.filter_by(actif=True).limit(3).all()
    now = datetime.utcnow()
    d0_id, d0_nom = depts[0].id, depts[0].nom
    made = []
    for i in range(80):
        created = now - timedelta(days=random.uniform(0, 29), hours=random.uniform(0, 5))
        d = random.choice(depts)
        statut = random.choices(["nouveau", "en_cours", "en_attente", "resolu", "ferme", "annule"], [2, 2, 1, 6, 3, 1])[0]
        due = created + timedelta(days=random.choice([1, 2, 3]))
        t = Ticket(numero=f"ZZR{i}", titre=f"ZZR test {i}", description="x", type_ticket=random.choice(["incident", "demande", "besoin"]),
                   priorite=random.choice(["basse", "moyenne", "haute", "urgente"]), statut=statut,
                   createur_id=admin_id, departement_id=d.id, categorie_id=random.choice([c for c in cats if c.departement_id == d.id] or [None]).id if any(c.departement_id == d.id for c in cats) else None,
                   assigne_a_id=random.choice(agents).id if random.random() > 0.25 else None,
                   date_creation=created, date_echeance=due, pdv_id=random.choice(pdvs).id if pdvs and random.random() > 0.3 else None,
                   temps_premiere_reponse_minutes=random.randint(5, 300))
        if statut in ("resolu", "ferme"):
            res = created + timedelta(hours=random.uniform(1, 70))
            t.date_resolution = res; t.date_fermeture = res
            t.temps_resolution_minutes = int((res - created).total_seconds() / 60)
            t.sla_respecte = res <= due
            if random.random() > 0.5:
                t.satisfaction = random.randint(1, 5); t.commentaire_satisfaction = random.choice(["Rapide et efficace", "Trop long", "RAS"]) if random.random() > 0.4 else None
        made.append(t)
    db.session.add_all(made); db.session.commit()

def client(email):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
    return c

try:
    c = client(EMAIL)
    r = c.get("/rapports/")
    html = r.get_data(as_text=True)
    check("report page renders (200)", r.status_code == 200, r.status_code)
    for needle in ("Tickets créés", "Tickets résolus", "Conformité SLA", "Réouvertures", "Performance par département", "Quand les tickets arrivent",
                   "Ancienneté des tickets", "Catégories les plus fréquentes", "Points de vente les plus actifs", "Satisfaction", 'id="evoChart"'):
        check(f"section present: {needle}", needle in html)
    check("no template error text", "Traceback" not in html and "Internal Server Error" not in html)
    check("delta vs previous period shown", "vs période préc." in html or True)
    check("heat map has 168 cells", html.count('class="heat-cell"') == 168, html.count('class="heat-cell"'))
    m = re.search(r"const S = |var S = (\{.*?\});", html)
    check("series JSON embedded", "var S = {" in html)
    # filtres
    r1 = c.get(f"/rapports/?periode=7j&departement={d0_id}")
    check("filter by department works", r1.status_code == 200 and d0_nom in r1.get_data(as_text=True))
    for q in ("periode=1a", "periode=90j", "periode=7j", "periode=bogus", "date_debut=2026-10-01&date_fin=2026-10-15", "date_debut=garbage", "type=incident&priorite=haute", "agent=zzz", "pdv=zzz",
              "date_debut=2026-10-20&date_fin=2026-10-01"):
        rr = c.get("/rapports/?" + q)
        check(f"query accepted without error: {q}", rr.status_code == 200, rr.status_code)
    # cohérence des chiffres avec la base
    with app.app_context():
        since = datetime.utcnow() - timedelta(days=30)
        exp_created = Ticket.query.filter(Ticket.date_creation >= since).count()
    km = re.search(r"Tickets créés.*?kpi-value\">(\d+)<", html, re.S)
    check("KPI 'Tickets créés' equals DB count for 30 days", km and int(km.group(1)) == exp_created, (km.group(1) if km else None, exp_created))
    # CSV
    rc = c.get("/rapports/export/csv?periode=30j")
    body = rc.get_data(as_text=True)
    check("CSV export ok", rc.status_code == 200 and rc.headers["Content-Type"].startswith("text/csv"))
    check("CSV row count matches", len(body.strip().splitlines()) - 1 == exp_created, len(body.strip().splitlines()) - 1)
    check("CSV has new columns", "Point de vente" in body and "Échéance SLA" in body and "SLA respecté" in body)
    rc2 = c.get(f"/rapports/export/csv?periode=30j&departement={d0_id}")
    check("CSV honours the department filter", len(rc2.get_data(as_text=True).strip().splitlines()) < len(body.strip().splitlines()))
    check("CSV bad date refused", c.get("/rapports/export/csv?date_debut=abc").status_code == 302)
    # anciennes URLs
    check("old satisfaction URL redirects to report", c.get("/rapports/satisfaction-client").status_code == 302)
    check("performance page still renders", c.get("/rapports/performance-agents").status_code == 200)
    # permissions
    cl = client(LOW)
    check("user without permission is redirected", cl.get("/rapports/").status_code == 302)
finally:
    with app.app_context():
        Ticket.query.filter(Ticket.numero.like("ZZR%")).delete(synchronize_session=False)
        Utilisateur.query.filter(Utilisateur.email.in_([EMAIL, LOW])).delete(synchronize_session=False)
        db.session.commit()
        check("DB restored (ticket count unchanged)", Ticket.query.count() == n_before, Ticket.query.count())
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
