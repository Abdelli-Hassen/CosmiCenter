import os, re, sys, secrets, random
from datetime import datetime, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Ticket, Departement

app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

PW = "T3st-" + secrets.token_urlsafe(8); EMAIL = "zz.ag.admin@example.invalid"; LOW = "zz.ag.low@example.invalid"
random.seed(5)
with app.app_context():
    sa = Role.query.filter_by(nom="Super Administrateur").first()
    low = Role.query.filter(Role.niveau <= 10).first()
    admin = Utilisateur(nom="AG", prenom="Admin", email=EMAIL, role_id=sa.id); admin.set_password(PW)
    lowu = Utilisateur(nom="AG", prenom="Low", email=LOW, role_id=low.id); lowu.set_password(PW)
    db.session.add_all([admin, lowu]); db.session.commit()
    admin_id = admin.id
    n_before = Ticket.query.count()
    depts = Departement.query.filter_by(actif=True).limit(3).all()
    agents = Utilisateur.query.filter(Utilisateur.actif == True, Utilisateur.email.notin_([EMAIL, LOW])).limit(3).all()
    ag_ids = [a.id for a in agents]; ag_names = [a.nom_complet for a in agents]
    now = datetime.utcnow()
    for i in range(60):
        created = now - timedelta(days=random.uniform(0, 28))
        statut = random.choices(["nouveau", "en_cours", "resolu", "ferme"], [2, 3, 6, 2])[0]
        due = created + timedelta(days=random.choice([1, 2]))
        t = Ticket(numero=f"ZZA{i}", titre=f"Ticket agent {i}", description="x", type_ticket="incident", priorite=random.choice(["basse", "haute", "urgente"]),
                   statut=statut, createur_id=admin_id, departement_id=random.choice(depts).id, assigne_a_id=random.choice(ag_ids),
                   date_creation=created, date_echeance=due, temps_premiere_reponse_minutes=30)
        if statut in ("resolu", "ferme"):
            res = created + timedelta(hours=random.uniform(1, 60))
            t.date_resolution = res; t.date_fermeture = res; t.temps_resolution_minutes = int((res - created).total_seconds() / 60)
            t.sla_respecte = res <= due; t.satisfaction = random.choice([None, 4, 5, 2])
        db.session.add(t)
    db.session.commit()
    since = now - timedelta(days=30)
    exp_resolved = Ticket.query.filter(Ticket.assigne_a_id == ag_ids[0], Ticket.statut.in_(["resolu", "ferme"]), Ticket.date_resolution >= since, Ticket.date_resolution <= datetime.utcnow()).count()
    exp_open = Ticket.query.filter(Ticket.assigne_a_id == ag_ids[0], Ticket.statut.in_(["nouveau", "ouvert", "en_cours", "en_attente"])).count()

def client(email):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
    return c

try:
    c = client(EMAIL)
    r = c.get("/rapports/performance-agents"); html = r.get_data(as_text=True)
    check("list page renders", r.status_code == 200, r.status_code)
    for needle in ("Le podium", "Classement", "Agents actifs", "Tickets résolus", "Respect du SLA", "En retard maintenant", "Sans agent", "Situation"):
        check(f"present: {needle}", needle in html)
    check("all 3 agents listed", all(n in html for n in ag_names))
    check("big info box is gone", "Comment lire cette page" not in html and "help-box" not in html)
    check("podium shows 3 cards", html.count('class="podium-card"') == 3, html.count('class="podium-card"'))
    check("column hints present", html.count("info-tip") >= 6, html.count("info-tip"))
    check("no raw error", "Traceback" not in html and "UndefinedError" not in html)
    for p in ("7j", "90j", "1a", "bogus"):
        check(f"period {p} ok", c.get(f"/rapports/performance-agents?periode={p}").status_code == 200)
    # la ligne de l'agent 0 doit afficher ses chiffres de la base
    row = re.search(re.escape(ag_names[0]) + r".*?</tr>", html[html.index("<table"):], re.S).group(0)
    nums = re.findall(r'class="num[^"]*">(?:<span[^>]*>)?(\d+)', row)
    check("row numbers match DB (resolved, in progress)", nums[:2] == [str(exp_resolved), str(exp_open)], (nums[:2], exp_resolved, exp_open))
    # sous-page
    d = c.get(f"/rapports/performance-agents/{ag_ids[0]}/tickets"); dh = d.get_data(as_text=True)
    check("agent page renders", d.status_code == 200, d.status_code)
    for needle in ("Tous les agents", "À traiter maintenant", "Tickets résolus sur la période", "Respect du SLA", "équipe :", "a résolu"):
        check(f"agent page present: {needle}", needle in dh)
    check("agent page shows the same resolved count", f"{exp_resolved} ticket" in dh, exp_resolved)
    check("agent page lists ticket links", dh.count("/tickets/") >= exp_open)
    for p in ("7j", "90j", "1a", "xx"):
        check(f"agent page period {p} ok", c.get(f"/rapports/performance-agents/{ag_ids[0]}/tickets?periode={p}").status_code == 200)
    check("unknown agent -> 404", c.get("/rapports/performance-agents/does-not-exist/tickets").status_code == 404)
    check("old satisfaction page still redirects", c.get("/rapports/satisfaction-client").status_code == 302)
    cl = client(LOW)
    check("no permission: list refused", cl.get("/rapports/performance-agents").status_code == 302)
    check("no permission: agent page refused", cl.get(f"/rapports/performance-agents/{ag_ids[0]}/tickets").status_code == 302)
finally:
    with app.app_context():
        Ticket.query.filter(Ticket.numero.like("ZZA%")).delete(synchronize_session=False)
        Utilisateur.query.filter(Utilisateur.email.in_([EMAIL, LOW])).delete(synchronize_session=False)
        db.session.commit()
        check("DB restored", Ticket.query.count() == n_before, Ticket.query.count())
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
