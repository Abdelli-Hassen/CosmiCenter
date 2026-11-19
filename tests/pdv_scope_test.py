"""Points de vente : sans `pdv.tous`, on ne peut modifier / gérer le matériel / les employés / la couleur que de SES PDV.

Autonome : utilisateurs `zz.*@example.invalid`, PDV `ZZ…`, tout est supprimé dans un `finally`.
Lancer : .\\venv\\Scripts\\python.exe tests\\pdv_scope_test.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from models import db, Utilisateur, Role, Permission, PointDeVente, Equipement  # noqa: E402

PW = "Passw0rd-zz-123"
app = create_app()
results = []


def check(label, ok):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + label)


def client_for(email):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
    c.tok = tok
    return c


with app.app_context():
    base = (Utilisateur.query.count(), PointDeVente.query.count())
    codes = ["pdv.voir", "pdv.modifier", "pdv.supprimer", "pdv.gerer_employes", "equipements.gerer"]
    perms = {p.code: p for p in Permission.query.filter(Permission.code.in_(codes + ["pdv.tous"])).all()}
    check("la permission pdv.tous existe", "pdv.tous" in perms)

    def mkrole(nom, extra=()):
        r = Role(nom=nom, description="zz", couleur="#123456", actif=True, systeme=False)
        r.permissions = [perms[c] for c in list(codes) + list(extra)]
        db.session.add(r)
        return r

    r_own, r_all = mkrole("ZZ own"), mkrole("ZZ all", ["pdv.tous"])
    pa, pb, pc = (PointDeVente(nom=f"ZZ PDV {x}", categorie="Urbain", actif=True) for x in "ABC")
    db.session.add_all([pa, pb, pc]); db.session.flush()
    u_own = Utilisateur(nom="ZZown", prenom="T", email="zz.own@example.invalid", actif=True, role_id=r_own.id)
    u_all = Utilisateur(nom="ZZall", prenom="T", email="zz.all@example.invalid", actif=True, role_id=r_all.id)
    for u in (u_own, u_all):
        u.set_password(PW); db.session.add(u)
    u_own.set_pdvs([pa.id, pb.id])           # A principal, B supplémentaire ; C ne lui appartient pas
    eq_c = Equipement(pdv_id=pc.id, type_equipement="ZZ cam", statut="actif")
    db.session.add(eq_c); db.session.commit()
    ids = dict(A=pa.id, B=pb.id, C=pc.id, eq=eq_c.id, own=u_own.id)

try:
    co = client_for("zz.own@example.invalid")
    A, B, C = ids["A"], ids["B"], ids["C"]
    form = lambda n: {"nom": n, "categorie": "Urbain", "csrf_token": co.tok(f"/pdv/{A}")}

    check("son PDV principal : formulaire de modification accessible", co.get(f"/pdv/{A}/modifier").status_code == 200)
    check("son PDV supplémentaire : formulaire accessible", co.get(f"/pdv/{B}/modifier").status_code == 200)
    r = co.get(f"/pdv/{C}/modifier")
    check("PDV d'un autre : formulaire refusé (redirection)", r.status_code == 302)
    co.post(f"/pdv/{C}/modifier", data=form("ZZ PDV C piraté"))
    co.post(f"/pdv/{B}/modifier", data=form("ZZ PDV B ok"))
    with app.app_context():
        check("PDV d'un autre : nom inchangé", db.session.get(PointDeVente, C).nom == "ZZ PDV C")
        check("son PDV : nom modifié", db.session.get(PointDeVente, B).nom == "ZZ PDV B ok")

    tok = co.tok(f"/pdv/{A}")
    r = co.post(f"/pdv/{C}/couleur", json={"couleur": "#ff0000"}, headers={"X-CSRFToken": tok})
    check("couleur d'un autre PDV : 403", r.status_code == 403)
    r = co.post(f"/pdv/{A}/couleur", json={"couleur": "#ff0000"}, headers={"X-CSRFToken": tok})
    check("couleur de son PDV : acceptée", r.status_code == 200)

    co.post(f"/pdv/{C}/equipement/nouveau", data={"type_equipement": "ZZ intrus", "csrf_token": tok})
    co.post(f"/pdv/equipement/{ids['eq']}/supprimer", data={"csrf_token": tok})
    co.post(f"/pdv/{A}/equipement/nouveau", data={"type_equipement": "ZZ à moi", "csrf_token": tok})
    with app.app_context():
        check("matériel d'un autre PDV : ni ajout ni suppression",
              Equipement.query.filter_by(pdv_id=C, type_equipement="ZZ intrus").count() == 0
              and db.session.get(Equipement, ids["eq"]) is not None)
        check("matériel de son PDV : ajout accepté", Equipement.query.filter_by(pdv_id=A, type_equipement="ZZ à moi").count() == 1)

    co.post(f"/pdv/{C}/employe/ajouter", data={"utilisateur_id": ids["own"], "csrf_token": tok})
    with app.app_context():
        check("employés d'un autre PDV : ajout refusé", db.session.get(Utilisateur, ids["own"]).pdv_id == A)
    co.post(f"/pdv/{B}/employe/retirer/{ids['own']}", data={"csrf_token": tok})
    with app.app_context():
        u = db.session.get(Utilisateur, ids["own"])
        check("retrait d'un PDV supplémentaire : seul celui-là est retiré",
              [p.id for p in u.tous_pdvs] == [A])

    html = co.get(f"/pdv/{C}").get_data(as_text=True)
    check("fiche d'un autre PDV : pas de bouton Modifier", f"/pdv/{C}/modifier" not in html)
    check("fiche de son PDV : bouton Modifier visible", f"/pdv/{A}/modifier" in co.get(f"/pdv/{A}").get_data(as_text=True))
    lst = co.get("/pdv/").get_data(as_text=True)
    check("liste : crayon seulement sur ses PDV", f"/pdv/{A}/modifier" in lst and f"/pdv/{C}/modifier" not in lst)

    ca = client_for("zz.all@example.invalid")
    check("avec pdv.tous : peut modifier n'importe quel PDV", ca.get(f"/pdv/{C}/modifier").status_code == 200)
    ca.post(f"/pdv/{C}/modifier", data={"nom": "ZZ PDV C admin", "categorie": "Urbain", "csrf_token": ca.tok(f"/pdv/{C}")})
    with app.app_context():
        check("avec pdv.tous : modification appliquée", db.session.get(PointDeVente, C).nom == "ZZ PDV C admin")
finally:
    with app.app_context():
        Equipement.query.filter(Equipement.type_equipement.like("ZZ%")).delete(synchronize_session=False)
        Utilisateur.query.filter(Utilisateur.email.like("zz.%@example.invalid")).delete(synchronize_session=False)
        PointDeVente.query.filter(PointDeVente.nom.like("ZZ PDV%")).delete(synchronize_session=False)
        for r in Role.query.filter(Role.nom.like("ZZ %")).all():
            db.session.delete(r)
        db.session.commit()
        after = (Utilisateur.query.count(), PointDeVente.query.count())
        check(f"retour à la base de référence {base}", after == base)

print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
