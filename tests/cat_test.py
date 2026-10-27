import os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Permission, CategorieTicket, Departement, Ticket

app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

PW = "T3st-" + secrets.token_urlsafe(8)
ADMIN, LOW = "zz.cat.admin@example.invalid", "zz.cat.low@example.invalid"
with app.app_context():
    sa = Role.query.filter_by(nom="Super Administrateur").first()
    low_role = Role(nom="ZZ Role Test", niveau=30, systeme=False, actif=True)
    db.session.add(low_role); db.session.flush()
    for em, rid in ((ADMIN, sa.id), (LOW, low_role.id)):
        u = Utilisateur(nom="CAT", prenom="Test", email=em, role_id=rid); u.set_password(PW); db.session.add(u)
    db.session.commit()
    low_role_id = low_role.id
    dept = Departement.query.filter_by(nom="Stock").first(); dept_id = dept.id
    perm = Permission.query.filter_by(code="admin.categories").first()
    check("permission admin.categories auto-created at startup", perm is not None)
    used = db.session.query(CategorieTicket).join(Ticket, Ticket.categorie_id == CategorieTicket.id).first()
    used_id = used.id if used else None
    n_before = CategorieTicket.query.count()

def client(email):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
    return c, tok

def cat(nom):
    with app.app_context():
        c = CategorieTicket.query.filter_by(nom=nom).first()
        return None if c is None else (c.id, c.actif, c.archivee, c.delai_resolution_jours, c.type_ticket, c.priorite_defaut)

try:
    # --- rôle sans permission
    c, tok = client(LOW)
    r = c.get("/admin/categories")
    check("role without permission: page refused", r.status_code == 302)
    check("role without permission: no button on new ticket page", "Gérer les catégories" not in c.get("/tickets/nouveau").get_data(as_text=True))
    t = tok("/tickets/nouveau")
    c.post("/admin/categories/creer", data={"nom": "ZZ-Nope", "departement_id": dept_id, "csrf_token": t})
    check("role without permission: cannot create", cat("ZZ-Nope") is None)

    # --- on donne la permission
    with app.app_context():
        rr = db.session.get(Role, low_role_id)
        pp = Permission.query.filter_by(code="admin.categories").first()
        rr.permissions.append(pp)
        db.session.commit()
    c, tok = client(LOW)
    html = c.get("/tickets/nouveau").get_data(as_text=True)
    check("with permission: button 'Gérer les catégories' on new ticket page", "Gérer les catégories" in html and "/admin/categories" in html)
    page = c.get("/admin/categories")
    check("with permission: page opens (200)", page.status_code == 200)
    body = page.get_data(as_text=True)
    check("page lists columns Type/Priorité/Délai/Tickets and 42+ rows", all(x in body for x in ("Priorité", "Délai", "Tickets")) and body.count("<tr data-type") >= 42, body.count("<tr data-type"))
    check("Retour goes back to new ticket for non-admin", "window.location.href='/tickets/nouveau'" in body)

    t = tok("/admin/categories")
    # --- créer
    c.post("/admin/categories/creer", data={"nom": "ZZ-Test", "departement_id": dept_id, "type_ticket": "incident", "priorite_defaut": "haute", "delai_resolution_jours": "3", "couleur": "#112233", "csrf_token": t})
    row = cat("ZZ-Test")
    check("create works (type/priority/delay saved)", row and row[3] == 3 and row[4] == "incident" and row[5] == "haute", row)
    c.post("/admin/categories/creer", data={"nom": "zz-test", "departement_id": dept_id, "csrf_token": t})
    with app.app_context():
        check("duplicate name in same department refused", CategorieTicket.query.filter(db.func.lower(CategorieTicket.nom) == "zz-test").count() == 1)
    c.post("/admin/categories/creer", data={"nom": "ZZ-Bad", "departement_id": dept_id, "delai_resolution_jours": "0", "csrf_token": t})
    check("invalid delay refused", cat("ZZ-Bad") is None)
    cid = row[0]
    # --- modifier
    c.post(f"/admin/categories/{cid}/modifier", data={"nom": "ZZ-Test2", "departement_id": dept_id, "type_ticket": "demande", "priorite_defaut": "basse", "delai_resolution_jours": "5", "couleur": "#ABCDEF", "csrf_token": t})
    row = cat("ZZ-Test2")
    check("edit works", row and row[3] == 5 and row[4] == "demande" and row[5] == "basse", row)
    check("old name gone after edit", cat("ZZ-Test") is None)
    # --- visible dans le formulaire
    check("active category shown in new-ticket form", ">ZZ-Test2<" in c.get("/tickets/nouveau").get_data(as_text=True))
    # --- désactiver
    c.post(f"/admin/categories/{cid}/toggle", data={"csrf_token": t})
    check("deactivate hides it from the form", cat("ZZ-Test2")[1] is False and f">ZZ-Test2<" not in c.get("/tickets/nouveau").get_data(as_text=True))
    c.post(f"/admin/categories/{cid}/toggle", data={"csrf_token": t})
    # --- archiver
    c.post(f"/admin/categories/{cid}/archiver", data={"csrf_token": t})
    row = cat("ZZ-Test2")
    check("archive: archived + inactive, hidden from form", row[2] is True and row[1] is False and f">ZZ-Test2<" not in c.get("/tickets/nouveau").get_data(as_text=True))
    check("archived row is flagged in the list", 'data-statut="archivee"' in c.get("/admin/categories").get_data(as_text=True))
    c.post(f"/admin/categories/{cid}/archiver", data={"csrf_token": t})
    row = cat("ZZ-Test2")
    check("restore: no longer archived (still inactive)", row[2] is False and row[1] is False)
    # --- supprimer : catégorie utilisée -> refusée
    if used_id:
        c.post(f"/admin/categories/{used_id}/supprimer", data={"csrf_token": t})
        with app.app_context():
            check("delete refused for a category used by tickets", db.session.get(CategorieTicket, used_id) is not None)
    # --- supprimer : catégorie vide
    c.post(f"/admin/categories/{cid}/supprimer", data={"csrf_token": t})
    check("delete works for an unused category", cat("ZZ-Test2") is None)
    # --- sans CSRF
    r = c.post("/admin/categories/creer", data={"nom": "ZZ-NoCsrf", "departement_id": dept_id})
    check("POST without CSRF token rejected", cat("ZZ-NoCsrf") is None and r.status_code in (400, 403))
    # --- super admin
    ca, toka = client(ADMIN)
    check("super admin: page opens", ca.get("/admin/categories").status_code == 200)
    check("super admin: button shown", "Gérer les catégories" in ca.get("/tickets/nouveau").get_data(as_text=True))
finally:
    with app.app_context():
        for nom in ("ZZ-Test", "ZZ-Test2", "ZZ-Bad", "ZZ-NoCsrf", "ZZ-Nope"):
            CategorieTicket.query.filter_by(nom=nom).delete()
        Utilisateur.query.filter(Utilisateur.email.in_([ADMIN, LOW])).delete(synchronize_session=False)
        r = db.session.get(Role, low_role_id)
        if r:
            r.permissions.clear(); db.session.delete(r)
        db.session.commit()
        check("DB restored (category count unchanged)", CategorieTicket.query.count() == n_before, CategorieTicket.query.count())
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
