import io, os, re, sys, secrets
from datetime import datetime, timedelta
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Ticket, Departement, Notification, HistoriqueTicket
app = create_app("development")
app.config["MAIL_USERNAME"] = None; app.config["MAIL_PASSWORD"] = None  # aucun e-mail réel
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

PW = "T3st-" + secrets.token_urlsafe(8)
E_ADM, E_USR = "zz.nav.admin@example.invalid", "zz.nav.user@example.invalid"
with app.app_context():
    sup = Role.query.filter_by(nom="Super Administrateur").first(); pdv_role = Role.query.filter_by(nom="Personnel Point de Vente").first()
    dept = Departement(nom="ZZ-NAV-DEPT", code="ZZNAV", sla_resolution_heures=48); db.session.add(dept); db.session.flush()
    adm = Utilisateur(nom="NAV", prenom="Admin", email=E_ADM, role_id=sup.id, departement_id=dept.id); adm.set_password(PW)
    usr = Utilisateur(nom="NAV", prenom="User", email=E_USR, role_id=pdv_role.id, departement_id=dept.id); usr.set_password(PW)
    db.session.add_all([adm, usr]); db.session.commit(); admid, usrid, did = adm.id, usr.id, dept.id
    seq = tuple(db.session.execute(db.text("select last_value,is_called from ticket_numero_seq")).one())
ticket_ids = []
try:
    def client(email):
        c = app.test_client()
        tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
        c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
        c.tok = tok
        return c
    ca, cu = client(E_ADM), client(E_USR)
    t = ca.tok("/tickets/nouveau")
    # création de 3 tickets par l'utilisateur standard (département sans catégorie -> échéance = SLA du département)
    for i in range(3):
        cu.post("/tickets/nouveau", data={"titre": f"NAV-Bulk-{i}", "description": f"desc recherche-unique-{i}", "priorite": "haute",
                "type_ticket": "incident", "departement_id": did, "routing_type": "all", "csrf_token": cu.tok("/tickets/nouveau")})
    with app.app_context():
        ts = Ticket.query.filter(Ticket.titre.like("NAV-Bulk-%")).order_by(Ticket.titre).all(); ticket_ids = [x.id for x in ts]
        check("3 tickets created", len(ts) == 3)
        delta = (ts[0].date_echeance - ts[0].date_creation).total_seconds() / 3600
        check("due date falls back to the department SLA (48h) when no category", 47.5 < delta < 48.5, round(delta, 2))
    # recherche
    html = ca.get("/tickets/liste?q=recherche-unique-1").get_data(as_text=True)
    body = html.split("<tbody>")[1].split("</tbody>")[0]
    check("search by description finds the matching ticket only", "NAV-Bulk-1" in body and "NAV-Bulk-0" not in body and "NAV-Bulk-2" not in body)
    html = ca.get(f"/tickets/liste?q={ts[0].numero if False else ''}").get_data(as_text=True)
    with app.app_context(): num0 = db.session.get(Ticket, ticket_ids[0]).numero
    html = ca.get(f"/tickets/liste?q=%23{num0}").get_data(as_text=True)
    check("search by ticket number (#N) works", "NAV-Bulk-0" in html.split("<tbody>")[1].split("</tbody>")[0] and "NAV-Bulk-1" not in html.split("<tbody>")[1].split("</tbody>")[0])
    page = ca.get("/tickets/liste").get_data(as_text=True)
    check("list has Fermé / Annulé filters and the search box", "statut=ferme" in page and "statut=annule" in page and 'name="q"' in page)
    # actions groupées
    r = ca.post("/tickets/bulk", json={"ids": ticket_ids, "action": "statut", "value": "en_cours"}, headers={"X-CSRFToken": ca.tok("/tickets/liste")})
    with app.app_context(): st = [db.session.get(Ticket, i).statut for i in ticket_ids]
    check("bulk status change applied to the 3 tickets", r.status_code == 200 and st == ["en_cours"] * 3 and r.get_json()["updated"] == 3, st)
    r = ca.post("/tickets/bulk", json={"ids": ticket_ids[:2], "action": "assigner", "value": usrid}, headers={"X-CSRFToken": ca.tok("/tickets/liste")})
    with app.app_context(): asg = [db.session.get(Ticket, i).assigne_a_id for i in ticket_ids]
    check("bulk assignment applied to the 2 selected tickets", r.status_code == 200 and asg[:2] == [usrid] * 2 and asg[2] is None, r.get_json())
    r = ca.post("/tickets/bulk", json={"ids": ticket_ids, "action": "statut", "value": "hacked"}, headers={"X-CSRFToken": ca.tok("/tickets/liste")})
    check("bulk with an invalid status refused (400)", r.status_code == 400)
    r = cu.post("/tickets/bulk", json={"ids": ticket_ids, "action": "assigner", "value": admid}, headers={"X-CSRFToken": cu.tok("/tickets/liste")})
    check("bulk assign refused without the tickets.assigner permission (403)", r.status_code == 403, r.status_code)
    r = ca.post("/tickets/bulk", json={"ids": "x"}, headers={"X-CSRFToken": ca.tok("/tickets/liste")})
    check("bulk with a malformed payload refused (400)", r.status_code == 400)
    # satisfaction
    tid = ticket_ids[0]
    page = cu.get(f"/tickets/{tid}").get_data(as_text=True)
    check("no rating form while the ticket is not resolved", "Envoyer mon évaluation" not in page)
    with app.app_context():
        tk = db.session.get(Ticket, tid); tk.date_creation = datetime.utcnow() - timedelta(minutes=90); db.session.commit()
    ca.post(f"/tickets/{tid}/statut", data={"statut": "resolu", "csrf_token": ca.tok(f"/tickets/{tid}")})
    page = cu.get(f"/tickets/{tid}").get_data(as_text=True)
    check("rating form appears for the creator once resolved", "Envoyer mon évaluation" in page)
    check("other users do not get the rating form", "Envoyer mon évaluation" not in ca.get(f"/tickets/{tid}").get_data(as_text=True))
    r = ca.post(f"/tickets/{tid}/evaluer", data={"satisfaction": "5", "csrf_token": ca.tok(f"/tickets/{tid}")})
    with app.app_context(): check("non-creator cannot rate", db.session.get(Ticket, tid).satisfaction is None)
    cu.post(f"/tickets/{tid}/evaluer", data={"satisfaction": "9", "csrf_token": cu.tok(f"/tickets/{tid}")})
    with app.app_context(): check("rating outside 1..5 refused", db.session.get(Ticket, tid).satisfaction is None)
    cu.post(f"/tickets/{tid}/evaluer", data={"satisfaction": "4", "commentaire": "ok", "csrf_token": cu.tok(f"/tickets/{tid}")})
    with app.app_context(): tk = db.session.get(Ticket, tid); check("creator rating saved", tk.satisfaction == 4 and tk.commentaire_satisfaction == "ok")
    # rapports : heures et satisfaction
    html = ca.get("/rapports/").get_data(as_text=True)
    check("report shows 1.5h (not 90h) for a 90-minute resolution", "1,5 h" in html and "90,0 h" not in html)
    check("report shows the satisfaction average", "4,0 / 5" in html)
    # messagerie
    r = ca.get("/tickets/chat"); check("/tickets/chat redirects to /chat/", r.status_code == 302 and r.headers["Location"].endswith("/chat/"), r.headers.get("Location"))
    html = ca.get("/chat/").get_data(as_text=True)
    check("chat header has no hard-coded demo contact", "Amine Larbi" not in html and "Supprimer la conversation" not in html)
    # navigation
    html = ca.get("/tickets/tableau-bord").get_data(as_text=True)
    check("sidebar Messagerie links to /chat/", 'href="/chat/"' in html)
    check("keyboard a11y script included", "js/a11y.js" in html)
    # poll
    r = ca.get("/api/notifications/poll"); check("poll exposes the unopened-tickets and unread-messages counts", all(k in r.get_json()["data"] for k in ("unopened_tickets", "unread_messages")))
    # faq supprimé
    check("hard-coded FAQ pages removed (404)", ca.get("/tickets/faq").status_code == 404)
    # pdf -> téléchargement
    os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "tickets"), exist_ok=True)
    pdf = os.path.join(app.config["UPLOAD_FOLDER"], "tickets", "zz-nav-test.pdf"); open(pdf, "wb").write(b"%PDF-1.4 test")
    r = ca.get("/static/uploads/tickets/zz-nav-test.pdf")
    check("non-image uploads are served as attachments", "attachment" in r.headers.get("Content-Disposition", ""), r.headers.get("Content-Disposition"))
    r.close()
    os.remove(pdf)
    # préférence e-mail dans le profil
    cu.post("/parametres/profil/modifier", data={"nom": "NAV", "prenom": "User", "email": E_USR, "csrf_token": cu.tok("/parametres/profil")})
    with app.app_context(): check("e-mail notification preference saved (unchecked -> False)", db.session.get(Utilisateur, usrid).notifications_email is False)
    page = cu.get("/parametres/profil").get_data(as_text=True)
    check("profile shows the switch, no language selector", 'name="notifications_email"' in page and 'name="langue"' not in page)
    # filtre PDV dans l'annuaire
    page = ca.get("/utilisateurs/").get_data(as_text=True)
    check("users directory has the PDV filter", 'name="pdv"' in page)
finally:
    with app.app_context():
        for i in ticket_ids:
            x = db.session.get(Ticket, i)
            if x: db.session.delete(x)
        db.session.commit()
        Notification.query.filter(Notification.utilisateur_id.in_([admid, usrid])).delete(synchronize_session=False)
        for i in (admid, usrid):
            x = db.session.get(Utilisateur, i)
            if x: db.session.delete(x)
        d = db.session.get(Departement, did)
        if d: db.session.delete(d)
        db.session.commit()
        db.session.execute(db.text("select setval('ticket_numero_seq', :v, :c)"), {"v": seq[0], "c": seq[1]}); db.session.commit()
        print("cleanup done | users:", Utilisateur.query.count(), "| tickets:", Ticket.query.count(), "| sequence:", tuple(db.session.execute(db.text("select last_value,is_called from ticket_numero_seq")).one()))
print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
