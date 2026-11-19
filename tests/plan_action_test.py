"""Plan d'action personnel : chacun ne voit / modifie / termine / supprime / exporte que SES tâches (même un
Super Administrateur). Aucune donnée partagée.

Autonome : utilisateurs `zz.*@example.invalid`, tâches `ZZ…`, tout est supprimé dans un `finally`.
Lancer : .\\venv\\Scripts\\python.exe tests\\plan_action_test.py
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import openpyxl  # noqa: E402

from app import create_app  # noqa: E402
from models import db, Utilisateur, Role, Permission, PlanActionTask  # noqa: E402

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
    c.tok = lambda: tok("/admin/plan-action")
    return c


def excel_titles(resp):
    wb = openpyxl.load_workbook(io.BytesIO(resp.data))
    return {str(cell.value) for row in wb.active.iter_rows() for cell in row if cell.value}


with app.app_context():
    base = (Utilisateur.query.count(), PlanActionTask.query.count())
    codes = ["admin_plan_action.voir", "admin_plan_action.creer", "admin_plan_action.modifier",
             "admin_plan_action.supprimer", "admin_plan_action.exporter"]
    r = Role(nom="ZZ plan", description="zz", couleur="#123456", actif=True, systeme=False)
    r.permissions = Permission.query.filter(Permission.code.in_(codes)).all()
    sa = Role.query.filter_by(nom="Super Administrateur").first()
    db.session.add(r); db.session.flush()
    for tag, role in (("a", r), ("b", r), ("sa", sa)):
        u = Utilisateur(nom=f"ZZ{tag}", prenom="T", email=f"zz.plan.{tag}@example.invalid", actif=True, role_id=role.id)
        u.set_password(PW); db.session.add(u)
    db.session.commit()

try:
    ca, cb, cs = (client_for(f"zz.plan.{t}@example.invalid") for t in ("a", "b", "sa"))
    form = lambda c, titre: {"titre": titre, "date_debut": "2030-01-10T09:00", "csrf_token": c.tok()}

    ca.post("/admin/plan-action/creer", data=form(ca, "ZZ tache de A"))
    cb.post("/admin/plan-action/creer", data=form(cb, "ZZ tache de B"))
    with app.app_context():
        ta = PlanActionTask.query.filter_by(titre="ZZ tache de A").first()
        tb = PlanActionTask.query.filter_by(titre="ZZ tache de B").first()
        check("chaque tâche est rattachée à son créateur", ta and tb and ta.createur_id != tb.createur_id)
        ida, idb = ta.id, tb.id

    page_a = ca.get("/admin/plan-action").get_data(as_text=True)
    check("A voit sa tâche dans la page", "ZZ tache de A" in page_a)
    check("A ne voit pas la tâche de B dans la page", "ZZ tache de B" not in page_a)
    page_b = cb.get("/admin/plan-action").get_data(as_text=True)
    check("B voit la sienne mais pas celle de A", "ZZ tache de B" in page_b and "ZZ tache de A" not in page_b)
    page_s = cs.get("/admin/plan-action").get_data(as_text=True)
    check("un Super Administrateur ne voit pas non plus les tâches des autres",
          "ZZ tache de A" not in page_s and "ZZ tache de B" not in page_s)

    titres = lambda c: {e["title"] for e in c.get("/admin/api/plan-action/tasks").get_json()}
    check("calendrier (API) : A ne reçoit que sa tâche", {"ZZ tache de A"} <= titres(ca) and "ZZ tache de B" not in titres(ca))
    check("calendrier (API) : le Super Administrateur ne reçoit pas celles des autres",
          not ({"ZZ tache de A", "ZZ tache de B"} & titres(cs)))

    # B tente d'agir sur la tâche de A
    r1 = cb.post(f"/admin/plan-action/{ida}/modifier", data=form(cb, "ZZ piratée"))
    r2 = cb.post(f"/admin/plan-action/{ida}/terminer", data={"csrf_token": cb.tok()})
    r3 = cb.post(f"/admin/plan-action/{ida}/supprimer", data={"csrf_token": cb.tok()})
    r4 = cs.post(f"/admin/plan-action/{ida}/supprimer", data={"csrf_token": cs.tok()})
    check("modifier / terminer / supprimer la tâche d'un autre : 404 (même pour un Super Administrateur)",
          [r.status_code for r in (r1, r2, r3, r4)] == [404, 404, 404, 404])
    with app.app_context():
        t = db.session.get(PlanActionTask, ida)
        check("la tâche de A est intacte (titre, statut, toujours présente)",
              t is not None and t.titre == "ZZ tache de A" and t.statut == "planned")

    exp_b = excel_titles(cb.get("/admin/plan-action/export-excel"))
    exp_a = excel_titles(ca.get("/admin/plan-action/export-excel"))
    check("export Excel : B n'y trouve que sa tâche", "ZZ tache de B" in exp_b and "ZZ tache de A" not in exp_b)
    check("export Excel : A n'y trouve que la sienne", "ZZ tache de A" in exp_a and "ZZ tache de B" not in exp_a)

    # le propriétaire garde la main
    ca.post(f"/admin/plan-action/{ida}/modifier", data=form(ca, "ZZ tache de A (modifiee)"))
    ca.post(f"/admin/plan-action/{ida}/terminer", data={"csrf_token": ca.tok()})
    with app.app_context():
        t = db.session.get(PlanActionTask, ida)
        check("le propriétaire peut modifier sa tâche", t.titre == "ZZ tache de A (modifiee)")
        check("le propriétaire peut la terminer", t.statut == "completed")
    ca.post(f"/admin/plan-action/{ida}/supprimer", data={"csrf_token": ca.tok()})
    with app.app_context():
        check("le propriétaire peut la supprimer", db.session.get(PlanActionTask, ida) is None
              and db.session.get(PlanActionTask, idb) is not None)
finally:
    with app.app_context():
        PlanActionTask.query.filter(PlanActionTask.titre.like("ZZ%")).delete(synchronize_session=False)
        Utilisateur.query.filter(Utilisateur.email.like("zz.plan.%@example.invalid")).delete(synchronize_session=False)
        for r in Role.query.filter(Role.nom == "ZZ plan").all():
            db.session.delete(r)
        db.session.commit()
        after = (Utilisateur.query.count(), PlanActionTask.query.count())
        check(f"retour à la base de référence {base}", after == base)

print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
