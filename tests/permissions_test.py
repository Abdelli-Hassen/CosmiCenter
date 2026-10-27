"""Permissions : catalogue complet + application réelle des cases de la page Rôles.
- chaque permission utilisée dans le code (routes, gabarits) existe dans la base (donc cochable dans « Rôles ») ;
- un rôle de test avec seulement certaines cases ne peut faire que ces actions (Boîte à idées, plan d'action, rapports…) ;
- tout est supprimé en fin de test (rôle, utilisateur, idées de test)."""
import os, re, sys, glob, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
import services.email_service as es
es.send_email_notification = lambda *a, **k: None   # aucun e-mail réel
from models import db, Utilisateur, Role, Permission, Suggestion, Notification, HistoriqueTicket

app = create_app("development")
results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())


# 1) toutes les permissions utilisées dans le code existent --------------------------------------
pat = re.compile(r"""(?:has_permission|permission_required|require_permission|any_permission)\(\s*((?:['"][a-z_]+\.[a-z_]+['"]\s*,?\s*)+)""")
used = {}
for pattern in ("routes/*.py", "utils/*.py", "services/*.py", "templates/**/*.html", "app.py"):
    for f in glob.glob(os.path.join(ROOT, pattern), recursive=True):
        txt = open(f, encoding="utf-8", errors="ignore").read()
        for m in pat.finditer(txt):
            for code in re.findall(r"['\"]([a-z_]+\.[a-z_]+)['\"]", m.group(1)):
                used.setdefault(code, os.path.relpath(f, ROOT))
with app.app_context():
    existing = {p.code for p in Permission.query.all()}
    base = (Utilisateur.query.count(), Role.query.count(), Suggestion.query.count())
missing = sorted(c for c in used if c not in existing)
check("every permission checked in the code exists in the Roles page", not missing, [(c, used[c]) for c in missing])
check("page-by-page catalogue: ideas, plan d'action, reports, companies... have their own boxes",
      all(c in existing for c in ("idees.creer", "idees.voir_toutes", "idees.modifier", "idees.supprimer",
                                  "admin_plan_action.creer", "admin_plan_action.supprimer", "admin_plan_action.exporter",
                                  "rapports_globaux.exporter", "entreprises.archiver", "entreprises.gerer_collaborateurs",
                                  "pdv.gerer_employes", "pdv.referentiels", "departements.gerer_membres",
                                  "utilisateurs.activer", "tickets.commenter", "base_connaissance.voir_lecteurs")))

# 2) un rôle de test : « voir + proposer » seulement --------------------------------------------
PW = "T3st-" + secrets.token_urlsafe(8)
EM = "zz.perm@example.invalid"
with app.app_context():
    perms = Permission.query.filter(Permission.code.in_(["idees.voir", "idees.creer", "tickets.voir_mes"])).all()
    role = Role(nom="ZZ Role Test", niveau=20, description="test", actif=True)
    role.permissions = perms
    db.session.add(role)
    db.session.flush()
    u = Utilisateur(nom="PERM", prenom="Zz", email=EM, role_id=role.id)
    u.set_password(PW)
    db.session.add(u)
    db.session.commit()
    role_id = role.id
try:
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": EM, "password": PW, "csrf_token": tok("/auth/connexion")})

    r = c.get("/suggestions/")
    check("role with 'idees.voir' opens the ideas page", r.status_code == 200, r.status_code)
    html = r.get_data(as_text=True)
    check("page shows the 'new idea' button but no admin bar", "Nouvelle Suggestion" in html and "card-admin-bar" not in html)
    t = tok("/suggestions/")
    c.post("/suggestions/", data={"titre": "ZZ idee test", "description": "desc", "type_suggestion": "bug", "csrf_token": t})
    with app.app_context():
        s = Suggestion.query.filter_by(titre="ZZ idee test").first()
        check("'idees.creer' allows sending an idea", s is not None)
        sid = s.id if s else None
    c.post(f"/suggestions/{sid}/statut", data={"statut": "accepte", "csrf_token": t})
    with app.app_context():
        check("without 'idees.modifier' the status cannot be changed", db.session.get(Suggestion, sid).statut == "nouveau")
    c.post(f"/suggestions/{sid}/supprimer", data={"csrf_token": t})
    with app.app_context():
        check("without 'idees.supprimer' the idea cannot be deleted", db.session.get(Suggestion, sid) is not None)
    check("plan d'action page refused without its permission", c.get("/admin/plan-action", follow_redirects=False).status_code in (302, 403))
    check("global report export refused without its permission", c.get("/rapports/export/csv", follow_redirects=False).status_code in (302, 403))

    # on coche les cases manquantes dans le rôle → les actions deviennent possibles
    with app.app_context():
        r_ = db.session.get(Role, role_id)
        r_.permissions = Permission.query.filter(Permission.code.in_(
            ["idees.voir", "idees.creer", "idees.modifier", "idees.supprimer", "idees.voir_toutes", "tickets.voir_mes"])).all()
        db.session.commit()
    c.post(f"/suggestions/{sid}/statut", data={"statut": "accepte", "csrf_token": t})
    with app.app_context():
        check("with 'idees.modifier' the status changes", db.session.get(Suggestion, sid).statut == "accepte")
    check("with 'idees.modifier' the admin bar appears", "card-admin-bar" in c.get("/suggestions/").get_data(as_text=True))
    c.post(f"/suggestions/{sid}/supprimer", data={"csrf_token": t})
    with app.app_context():
        check("with 'idees.supprimer' the idea is deleted", db.session.get(Suggestion, sid) is None)
finally:
    with app.app_context():
        for s in Suggestion.query.filter(Suggestion.titre.like("ZZ idee%")).all():
            db.session.delete(s)
        uu = Utilisateur.query.filter_by(email=EM).first()
        if uu:
            HistoriqueTicket.query.filter_by(utilisateur_id=uu.id).delete()
            Notification.query.filter_by(utilisateur_id=uu.id).delete()
            db.session.commit()
            db.session.delete(uu)
        rr = Role.query.filter_by(nom="ZZ Role Test").first()
        if rr:
            rr.permissions = []
            db.session.commit()
            db.session.delete(rr)
        db.session.commit()
        now = (Utilisateur.query.count(), Role.query.count(), Suggestion.query.count())
        check("DB restored (users / roles / ideas unchanged)", now == base, (now, base))
print(f"\n{sum(results)}/{len(results)} checks passed")
