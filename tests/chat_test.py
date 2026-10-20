import io, os, re, shutil, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Message, Notification, Departement, Ticket, HistoriqueTicket
app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())

PW = "T3st-" + secrets.token_urlsafe(8)
EM = {"a": "zz.chat.a@example.invalid", "b": "zz.chat.b@example.invalid", "c": "zz.chat.c@example.invalid"}
PNG = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000d49444154789c6360000002000001e221bc330000000049454e44ae426082")
with app.app_context():
    role = Role.query.filter_by(nom="Responsable Point de Vente").first()  # a messagerie.voir
    ids = {}
    for k, e in EM.items():
        u = Utilisateur(nom="CHAT" + k.upper(), prenom="Zz", email=e, role_id=role.id); u.set_password(PW); db.session.add(u)
    db.session.commit()
    ids = {k: Utilisateur.query.filter_by(email=e).first().id for k, e in EM.items()}
    nb_before = Message.query.count()
files_to_clean = []
try:
    def client(k):
        c = app.test_client()
        tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
        c.post("/auth/connexion", data={"email": EM[k], "password": PW, "csrf_token": tok("/auth/connexion")}); c.tok = tok
        return c
    a, b, c3 = client("a"), client("b"), client("c")
    ta = a.tok("/chat/")
    # --- envoi d'une image + texte
    r = a.post("/chat/api/send", data={"receiver_id": ids["b"], "content": "voici une image", "file": (io.BytesIO(PNG), "capture écran.png"), "csrf_token": ta}, content_type="multipart/form-data")
    d = r.get_json(); mid = d.get("id")
    check("image + text message accepted", r.status_code == 200 and d["fichier"]["est_image"] and d["fichier"]["nom"] == "capture écran.png", r.status_code)
    with app.app_context():
        m = db.session.get(Message, mid)
        check("file metadata stored in the database", m.fichier_chemin and m.fichier_taille == len(PNG) and m.fichier_nom == "capture écran.png" and m.content == "voici une image")
        stored = os.path.join(app.instance_path, "chat_files", m.fichier_chemin); files_to_clean.append(stored)
        check("file stored outside the public static folder", os.path.isfile(stored) and "static" not in stored)
    # --- téléchargement : expéditeur et destinataire seulement
    r = b.get(f"/chat/fichier/{mid}"); check("receiver sees the image inline", r.status_code == 200 and r.mimetype == "image/png" and "attachment" not in (r.headers.get("Content-Disposition") or ""), r.mimetype)
    check("image bytes identical", r.data == PNG); r.close()
    r = a.get(f"/chat/fichier/{mid}"); check("sender can fetch it too", r.status_code == 200); r.close()
    r = c3.get(f"/chat/fichier/{mid}"); check("a third user cannot fetch it (404)", r.status_code == 404, r.status_code); r.close()
    r = app.test_client().get(f"/chat/fichier/{mid}"); check("anonymous cannot fetch it", r.status_code == 302, r.status_code); r.close()
    # --- tout type de fichier : exécutable, html, sans extension -> téléchargement forcé
    for name, data in [("setup.exe", b"MZ" + b"\0" * 50), ("page.html", b"<script>alert(1)</script>"), ("notes", b"abc"), ("archive.tar.gz", b"x" * 1000), ("اختبار.pdf", b"%PDF-1.4 x")]:
        r = a.post("/chat/api/send", data={"receiver_id": ids["b"], "content": "", "file": (io.BytesIO(data), name), "csrf_token": ta}, content_type="multipart/form-data")
        dd = r.get_json()
        ok = r.status_code == 200 and dd["fichier"] and not dd["fichier"]["est_image"]
        with app.app_context(): m2 = db.session.get(Message, dd["id"]); files_to_clean.append(os.path.join(app.instance_path, "chat_files", m2.fichier_chemin))
        g = b.get(f"/chat/fichier/{dd['id']}"); cd = g.headers.get("Content-Disposition") or ""; g.close()
        check(f"any file type accepted and downloaded as attachment: {name}", ok and "attachment" in cd, cd)
    # --- refus
    r = a.post("/chat/api/send", data={"receiver_id": ids["b"], "content": "", "csrf_token": ta}, content_type="multipart/form-data"); check("empty message (no text, no file) refused", r.status_code == 400)
    r = a.post("/chat/api/send", data={"receiver_id": ids["b"], "content": "x", "file": (io.BytesIO(b""), "vide.txt"), "csrf_token": ta}, content_type="multipart/form-data"); check("empty file refused", r.status_code == 400, r.status_code)
    r = a.post("/chat/api/send", data={"receiver_id": ids["a"], "content": "x", "csrf_token": ta}, content_type="multipart/form-data"); check("cannot message yourself", r.status_code == 400)
    r = a.post("/chat/api/send", data={"receiver_id": "nope", "content": "x", "csrf_token": ta}, content_type="multipart/form-data"); check("unknown receiver refused", r.status_code == 404)
    r = a.post("/chat/api/send", data={"receiver_id": ids["b"], "content": "x", "file": (io.BytesIO(b"1"), "x.bin")}, content_type="multipart/form-data"); check("upload without CSRF token refused", r.status_code == 400, r.status_code)
    r = a.post("/chat/api/send", json={"receiver_id": ids["b"], "content": "texte simple"}, headers={"X-CSRFToken": ta}); check("plain JSON text message still works", r.status_code == 200 and r.get_json()["fichier"] is None)
    # --- messages non lus / conversation / aperçu
    r = b.get("/api/notifications/poll"); n_unread = r.get_json()["data"]["unread_messages"]
    check("recipient sees the unread message count (7 messages)", n_unread == 7, n_unread)
    html = b.get("/tickets/tableau-bord").get_data(as_text=True)
    check("sidebar Messagerie badge shows the number (7)", re.search(r'id="navMessagesBadge"[^>]*>\s*7\s*<', html) is not None)
    convs = b.get("/chat/api/conversations").get_json()
    check("conversation list works with attachments (preview of the last message)", len(convs) == 1 and convs[0]["last_message"] == "texte simple", convs[0]["last_message"] if convs else None)
    msgs = b.get(f"/chat/api/messages/{ids['a']}").get_json()["messages"]
    check("conversation returns all 7 messages incl. file info", len(msgs) == 7 and sum(1 for x in msgs if x["fichier"]) == 6)
    check("opening the conversation marks them read", b.get("/api/notifications/poll").get_json()["data"]["unread_messages"] == 0)
    html = b.get("/tickets/tableau-bord").get_data(as_text=True)
    check("badge hidden once everything is read", 'id="navMessagesBadge" title="Messages non lus" style="display:none;"' in html)
    # --- aperçu d'un message sans texte
    with app.app_context():
        pass
    # --- page de chat
    page = a.get("/chat/").get_data(as_text=True)
    check("chat page has the attach button and file input", 'id="chatAttachBtn"' in page and 'id="chatFile"' in page)
    # --- badge tickets non ouverts
    with app.app_context():
        d = Departement.query.first(); t = Ticket(numero="999999", titre="ZZ-unopened", description="x", type_ticket="incident", createur_id=ids["a"], departement_id=None, assigne_a_id=ids["b"])
        db.session.add(t); db.session.commit(); tid = t.id
    n = b.get("/api/notifications/poll").get_json()["data"]["unopened_tickets"]; check("assigned, never-opened ticket counts as 'not opened' (1)", n == 1, n)
    check("creator does not count their own ticket", a.get("/api/notifications/poll").get_json()["data"]["unopened_tickets"] == 0)
    b.get(f"/tickets/{tid}")
    check("opening the ticket removes it from the count (0)", b.get("/api/notifications/poll").get_json()["data"]["unopened_tickets"] == 0)
    html = b.get("/tickets/tableau-bord").get_data(as_text=True)
    check("tickets badge hidden when nothing is unopened", 'id="navTicketsBadge" title="Tickets non ouverts" style="display:none;"' in html or 'navTicketsBadge' not in html)
finally:
    with app.app_context():
        for f in files_to_clean:
            if os.path.isfile(f): os.remove(f)
        t = Ticket.query.filter_by(numero="999999").first()
        if t: db.session.delete(t)
        Message.query.filter(Message.sender_id.in_(list(ids.values())) | Message.receiver_id.in_(list(ids.values()))).delete(synchronize_session=False)
        Notification.query.filter(Notification.utilisateur_id.in_(list(ids.values()))).delete(synchronize_session=False)
        db.session.commit()
        for u in Utilisateur.query.filter(Utilisateur.email.in_(list(EM.values()))).all(): db.session.delete(u)
        db.session.commit()
        left = [f for f in os.listdir(os.path.join(app.instance_path, "chat_files")) if os.path.join(app.instance_path, "chat_files", f) in files_to_clean]
        print("cleanup: messages", Message.query.count(), "(was", nb_before, ") | users", Utilisateur.query.count(), "| leftover chat files:", len(left))
print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
