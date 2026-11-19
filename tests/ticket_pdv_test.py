"""Tickets : destinataire = un département OU un point de vente (pour joindre les personnes en PDV, sans département).

Autonome : utilisateurs `zz.*@example.invalid`, PDV `ZZ…`, tickets `ZZ…`, tout est supprimé dans un `finally`.
Lancer : .\\venv\\Scripts\\python.exe tests\\ticket_pdv_test.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from models import db, Utilisateur, Role, Permission, PointDeVente, Ticket, Notification  # noqa: E402

PW = "Passw0rd-zz-123"
app = create_app()
results = []


def check(label, ok):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + label)


def mail(tag):
    return f"zz.tpdv.{tag}@example.invalid"


def client_for(tag):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": mail(tag), "password": PW, "csrf_token": tok("/auth/connexion")})
    c.tok = lambda: tok("/tickets/nouveau")
    return c


with app.app_context():
    base = (Utilisateur.query.count(), PointDeVente.query.count(), Ticket.query.count())
    role = Role(nom="ZZ tpdv", description="zz", couleur="#123456", actif=True, systeme=False)
    role.permissions = Permission.query.filter(Permission.code.in_(["tickets.creer", "tickets.voir_mes"])).all()
    db.session.add(role)
    p1, p2, p3 = (PointDeVente(nom=f"ZZ TPDV {x}", categorie="Urbain", actif=True) for x in "123")
    db.session.add_all([p1, p2, p3]); db.session.flush()

    def mk(tag, pdvs):
        u = Utilisateur(nom=f"ZZ{tag}", prenom="T", email=mail(tag), actif=True, role_id=role.id)
        u.set_password(PW); db.session.add(u); db.session.flush()
        if pdvs:
            u.set_pdvs(pdvs)
        return u.id

    ids = dict(
        sender=mk("sender", []),                    # écrit le ticket, aucun PDV
        leila=mk("leila", [p1.id]),                 # PDV 1, sans département
        extra=mk("extra", [p3.id, p1.id]),          # PDV 3 principal + PDV 1 en supplément
        other=mk("other", [p2.id]),                 # un autre PDV
        outsider=mk("outsider", [p3.id]),           # PDV 3 seulement : jamais visé
    )
    db.session.commit()
    P1, P2 = p1.id, p2.id

try:
    cs = client_for("sender")
    page = cs.get("/tickets/nouveau").get_data(as_text=True)
    check("formulaire : choix Département / Point de vente et liste des PDV",
          'name="dest_type"' in page and 'id="pdvChecks"' in page and 'name="pdv_ids"' in page and "ZZ TPDV 1" in page)
    check("formulaire : chaque personne porte la liste de ses PDV (pour filtrer)", f",{P1}," in page)

    def create(titre, **extra):
        data = {"titre": titre, "description": "zz", "priorite": "moyenne", "type_ticket": "incident",
                "routing_type": "all", "csrf_token": cs.tok()}
        data.update(extra)
        return cs.post("/tickets/nouveau", data=data)

    create("ZZ vers PDV 1", dest_type="pdv", pdv_ids=[P1])
    create("ZZ solo pour Leila", dest_type="pdv", pdv_ids=[P1], routing_type="specific", assigne_a_id=ids["leila"])
    create("ZZ mauvais agent", dest_type="pdv", pdv_ids=[P1], routing_type="specific", assigne_a_id=ids["other"])
    create("ZZ collab PDV", dest_type="pdv", pdv_ids=[P1], routing_type="collab")
    create("ZZ sans PDV", dest_type="pdv")
    create("ZZ PDV inconnu", dest_type="pdv", pdv_ids=[P1, "inexistant"])
    create("ZZ duo PDV", dest_type="pdv", pdv_ids=[P1, P2])
    create("ZZ multi pour other", dest_type="pdv", pdv_ids=[P1, P2], routing_type="specific", assigne_a_id=ids["other"])
    create("ZZ multi mauvais agent", dest_type="pdv", pdv_ids=[P1, P2], routing_type="specific", assigne_a_id=ids["outsider"])
    with app.app_context():
        t_all = Ticket.query.filter_by(titre="ZZ vers PDV 1").first()
        t_one = Ticket.query.filter_by(titre="ZZ solo pour Leila").first()
        check("ticket adressé à un PDV : pdv_id posé, aucun département", t_all and t_all.pdv_id == P1 and t_all.departement_id is None)
        check("ticket à une personne du PDV : assignée", t_one and t_one.assigne_a_id == ids["leila"] and t_one.pdv_id == P1)
        check("personne hors du PDV refusée", Ticket.query.filter_by(titre="ZZ mauvais agent").count() == 0)
        check("collaboration multiple refusée pour un PDV", Ticket.query.filter_by(titre="ZZ collab PDV").count() == 0)
        check("PDV obligatoire en mode PDV", Ticket.query.filter_by(titre="ZZ sans PDV").count() == 0)
        check("PDV inconnu parmi les PDV cochés : refusé", Ticket.query.filter_by(titre="ZZ PDV inconnu").count() == 0)
        t_multi = Ticket.query.filter_by(titre="ZZ duo PDV").first()
        check("plusieurs PDV : le premier dans pdv_id, les autres dans pdv_extra_ids, aucun département",
              t_multi and t_multi.pdv_id == P1 and t_multi.pdv_extra_ids == P2 and t_multi.departement_id is None
              and t_multi.pdv_cibles_ids == [P1, P2])
        check("plusieurs PDV + personne d'un des PDV cochés : acceptée",
              Ticket.query.filter_by(titre="ZZ multi pour other").count() == 1)
        check("plusieurs PDV + personne d'aucun des PDV cochés : refusée",
              Ticket.query.filter_by(titre="ZZ multi mauvais agent").count() == 0)
        tid_multi = t_multi.id
        n_multi = {n.utilisateur_id for n in Notification.query.filter(Notification.lien.like(f"%{tid_multi}%")).all()}
        check("plusieurs PDV : le personnel de CHAQUE PDV est notifié, pas les autres",
              {ids["leila"], ids["extra"], ids["other"]} <= n_multi and ids["outsider"] not in n_multi and ids["sender"] not in n_multi)
        tid_all = t_all.id
        notified = {n.utilisateur_id for n in Notification.query.filter(Notification.lien.like(f"%{tid_all}%")).all()}
        check("tout le personnel du PDV est notifié (principal ET supplémentaire), pas les autres",
              {ids["leila"], ids["extra"]} <= notified and ids["other"] not in notified and ids["sender"] not in notified)

    cl, ce, co = client_for("leila"), client_for("extra"), client_for("other")
    lst = lambda c: c.get("/tickets/mes-tickets").get_data(as_text=True)
    check("Leila (sans département, PDV 1) voit le ticket dans « Mes tickets »", "ZZ vers PDV 1" in lst(cl))
    check("sa fiche s'ouvre", cl.get(f"/tickets/{tid_all}").status_code == 200)
    check("PDV supplémentaire : la personne le voit aussi", "ZZ vers PDV 1" in lst(ce) and ce.get(f"/tickets/{tid_all}").status_code == 200)
    check("une personne d'un autre PDV ne le voit pas ni ne l'ouvre",
          "ZZ vers PDV 1" not in lst(co) and co.get(f"/tickets/{tid_all}").status_code != 200)
    check("la fiche affiche le point de vente", "ZZ TPDV 1" in cl.get(f"/tickets/{tid_all}").get_data(as_text=True))
    cx = client_for("outsider")
    check("ticket multi-PDV : visible et ouvrable par le personnel du 2e PDV",
          "ZZ duo PDV" in lst(co) and co.get(f"/tickets/{tid_multi}").status_code == 200)
    check("ticket multi-PDV : invisible et fermé pour un PDV non visé",
          "ZZ duo PDV" not in lst(cx) and cx.get(f"/tickets/{tid_multi}").status_code != 200)
    check("la fiche multi-PDV liste les deux points de vente",
          all(n in cl.get(f"/tickets/{tid_multi}").get_data(as_text=True) for n in ("ZZ TPDV 1", "ZZ TPDV 2")))

    # mode département inchangé
    r = cs.post("/tickets/nouveau", data={"titre": "ZZ sans destinataire", "description": "zz", "priorite": "moyenne",
                                          "type_ticket": "incident", "routing_type": "all", "csrf_token": cs.tok()})
    with app.app_context():
        check("mode département par défaut : inchangé (pdv_id vide)",
              Ticket.query.filter_by(titre="ZZ sans destinataire").first().pdv_id is None)
finally:
    with app.app_context():
        for t in Ticket.query.filter(Ticket.titre.like("ZZ %")).all():
            db.session.delete(t)          # suppression ORM : emporte l'historique, les tâches, les commentaires
        db.session.flush()
        Notification.query.filter(Notification.utilisateur_id.in_(
            db.session.query(Utilisateur.id).filter(Utilisateur.email.like("zz.tpdv.%@example.invalid")))).delete(synchronize_session=False)
        Utilisateur.query.filter(Utilisateur.email.like("zz.tpdv.%@example.invalid")).delete(synchronize_session=False)
        PointDeVente.query.filter(PointDeVente.nom.like("ZZ TPDV %")).delete(synchronize_session=False)
        for r in Role.query.filter(Role.nom == "ZZ tpdv").all():
            db.session.delete(r)
        db.session.commit()
        after = (Utilisateur.query.count(), PointDeVente.query.count(), Ticket.query.count())
        check(f"retour à la base de référence {base}", after == base)

print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
