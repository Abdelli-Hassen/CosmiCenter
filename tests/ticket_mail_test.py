"""E-mails d'un nouveau ticket : « Ticket envoyé » (créateur) + « Ticket reçu » (destinataires), contenu complet.
L'envoi SMTP est neutralisé (rien ne part) ; ticket et utilisateur de test supprimés en fin de test."""
import os, re, sys, io, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
import services.email_service as es
from models import db, Utilisateur, Role, Ticket, Departement, HistoriqueTicket, Notification
from PIL import Image

captured = []
es.send_email_batch = lambda app, subject, items: captured.append((subject, items))   # aucun envoi réel

app = create_app("development")
results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())


PW = "T3st-" + secrets.token_urlsafe(8)
EM = "zz.ticketmail@example.invalid"
with app.app_context():
    base = (Ticket.query.count(), Utilisateur.query.count())
    sup = Role.query.filter_by(nom="Super Administrateur").first()
    u = Utilisateur(nom="TMAIL", prenom="Zz", email=EM, role_id=sup.id)
    u.set_password(PW)
    db.session.add(u)
    db.session.commit()
    dept_id = Departement.query.filter_by(nom="IT").first().id
png = io.BytesIO()
Image.new("RGB", (60, 40), (220, 40, 60)).save(png, "PNG")
png.seek(0)
try:
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": EM, "password": PW, "csrf_token": tok("/auth/connexion")})
    desc = "Premiere ligne\nDetails <b>importants</b>\n" + ("Texte long. " * 100) + "\nDERNIERE LIGNE"
    r = c.post("/tickets/nouveau", data={
        "csrf_token": tok("/tickets/nouveau"), "titre": "ZZ ticket mail", "type_ticket": "incident",
        "departement_id": dept_id, "routing_type": "all", "description": desc, "priorite": "haute",
        "taches[]": ["etape A", "etape B"], "attachments": (png, "zz.png")}, content_type="multipart/form-data")
    check("ticket created", r.status_code == 302, r.status_code)
    subjects = [s for s, _ in captured]
    check("two mails: 'Ticket envoye' then 'Ticket recu'", len(captured) == 2 and subjects[0].startswith("Ticket envoy") and subjects[1].startswith("Ticket re"), subjects)
    sent, got = captured[0][1], captured[1][1]
    check("creator gets exactly one 'envoye' mail, addressed to them", len(sent) == 1 and sent[0][0] == EM)
    check("recipients get 'recu' mails, creator excluded", len(got) >= 1 and EM not in [a for a, _ in got], len(got))
    for label, html in (("envoye", sent[0][1]), ("recu", got[0][1])):
        txt = es._html_to_text(html)
        check(f"'{label}' mail is complete (greeting, full description, checklist, attachment, closing)",
              all(x in txt for x in ("Bonjour", "Premiere ligne", "DERNIERE LIGNE", "etape A", "etape B", "zz.png", "Cordialement")))
        check(f"'{label}' mail escapes HTML in the description", "<b>importants</b>" not in html and "&lt;b&gt;importants" in html)
    check("'envoye' banner says sent, 'recu' banner says received",
          "Ticket envoy" in sent[0][1] and "Ticket re" in got[0][1])
finally:
    with app.app_context():
        for t in Ticket.query.filter(Ticket.titre.like("ZZ ticket mail%")).all():
            db.session.delete(t)
        uu = Utilisateur.query.filter_by(email=EM).first()
        if uu:
            HistoriqueTicket.query.filter_by(utilisateur_id=uu.id).delete()
            Notification.query.filter_by(utilisateur_id=uu.id).delete()
            db.session.commit()
            db.session.delete(uu)
        db.session.commit()
        now = (Ticket.query.count(), Utilisateur.query.count())
        check("DB restored (tickets / users unchanged)", now == base, (now, base))
print(f"\n{sum(results)}/{len(results)} checks passed")
