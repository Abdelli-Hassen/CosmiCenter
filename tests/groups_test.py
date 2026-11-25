"""Messagerie : groupes de discussion (création, messages, droits, membres, fichiers, suppression)."""
import io, os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, Message, Notification, ChatGroupe, ChatGroupeMembre
app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())

PW = "T3st-" + secrets.token_urlsafe(8)
EM = {k: f"zz.grp.{k}@example.invalid" for k in "abcd"}
with app.app_context():
    role = Role.query.filter_by(nom="Responsable Point de Vente").first()  # a messagerie.voir
    for k, e in EM.items():
        u = Utilisateur(nom="GRP" + k.upper(), prenom="Zz", email=e, role_id=role.id); u.set_password(PW); db.session.add(u)
    db.session.commit()
    ids = {k: Utilisateur.query.filter_by(email=e).first().id for k, e in EM.items()}
    base = (Message.query.count(), ChatGroupe.query.count(), ChatGroupeMembre.query.count(), Utilisateur.query.count() - len(EM))  # sans les 4 comptes de test
files_to_clean = []
try:
    def client(k):
        c = app.test_client()
        tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
        c.post("/auth/connexion", data={"email": EM[k], "password": PW, "csrf_token": tok("/auth/connexion")}); c.tok = tok("/chat/")
        c.pj = lambda url, body=None: c.post(url, json=body or {}, headers={"X-CSRFToken": c.tok})
        return c
    a, b, c3, d = client("a"), client("b"), client("c"), client("d")

    # --- création
    check("empty name refused", a.pj("/chat/api/groupes", {"nom": "  ", "membres": [ids["b"]]}).status_code == 400)
    check("name too long refused", a.pj("/chat/api/groupes", {"nom": "x" * 61, "membres": [ids["b"]]}).status_code == 400)
    check("group without any other member refused", a.pj("/chat/api/groupes", {"nom": "ZZ seul", "membres": [ids["a"]]}).status_code == 400)
    check("invalid members payload refused", a.pj("/chat/api/groupes", {"nom": "ZZ x", "membres": "nope"}).status_code == 400)
    r = a.pj("/chat/api/groupes", {"nom": "ZZ Equipe", "membres": [ids["b"], ids["c"], ids["b"], "inconnu"]})
    g = r.get_json(); gid = g.get("id")
    check("group created by A with B and C (duplicates / unknown ids ignored)", r.status_code == 200 and gid, r.status_code)
    check("create without CSRF token refused", a.post("/chat/api/groupes", json={"nom": "ZZ y", "membres": [ids["b"]]}).status_code == 400)
    with app.app_context():
        ms = {m.utilisateur_id: m.est_admin for m in ChatGroupeMembre.query.filter_by(groupe_id=gid)}
        check("3 members, only the creator is admin", len(ms) == 3 and ms[ids["a"]] and not ms[ids["b"]] and not ms[ids["c"]])
        check("members B and C were notified", Notification.query.filter_by(utilisateur_id=ids["b"], titre="Nouveau groupe").count() == 1 and Notification.query.filter_by(utilisateur_id=ids["a"], titre="Nouveau groupe").count() == 0)

    # --- liste des conversations
    for who, cl in (("a", a), ("b", b), ("c", c3)):
        convs = cl.get("/chat/api/conversations").get_json()
        check(f"{who.upper()} sees the group in the conversation list", len(convs) == 1 and convs[0]["is_group"] and convs[0]["contact_id"] == gid and convs[0]["contact_name"] == "ZZ Equipe" and convs[0]["nb_membres"] == 3, convs)
    check("outsider D sees no conversation", d.get("/chat/api/conversations").get_json() == [])

    # --- messages
    r = b.pj("/chat/api/send", {"groupe_id": gid, "content": "salut le groupe"})
    check("member B posts in the group", r.status_code == 200 and r.get_json()["groupe_id"] == gid and r.get_json()["sender_name"] == "Zz GRPB", r.status_code)
    convs = a.get("/chat/api/conversations").get_json()
    check("A has 1 unread message and a preview with the author", convs[0]["unread_count"] == 1 and convs[0]["last_message"] == "Zz : salut le groupe", convs[0])
    check("B (the sender) has 0 unread", b.get("/chat/api/conversations").get_json()[0]["unread_count"] == 0)
    pj = a.get("/api/notifications/poll").get_json()["data"]
    check("sidebar badge counts the group message (1) and notifications are typed 'chat'", pj["unread_messages"] == 1 and all(n["type"] == "chat" for n in pj["notifications"]), pj["unread_messages"])
    check("sender B has no unread badge from his own message", b.get("/api/notifications/poll").get_json()["data"]["unread_messages"] == 0)
    check("page-load sidebar badge shows 1 for A", re.search(r'id="navMessagesBadge"[^>]*>\s*1\s*<', a.get("/tickets/tableau-bord").get_data(as_text=True)) is not None)
    with app.app_context():
        check("A and C notified, sender B not", Notification.query.filter_by(utilisateur_id=ids["a"], type_notification="chat", titre="Groupe « ZZ Equipe »").count() == 1
              and Notification.query.filter_by(utilisateur_id=ids["c"], titre="Groupe « ZZ Equipe »").count() == 1
              and Notification.query.filter_by(utilisateur_id=ids["b"], titre="Groupe « ZZ Equipe »").count() == 0)
    data = a.get(f"/chat/api/groupe/{gid}").get_json()
    check("A opens the group: messages + members + admin flag", len(data["messages"]) == 1 and data["groupe"]["nb_membres"] == 3 and data["groupe"]["is_admin"] is True and data["messages"][0]["sender_name"] == "Zz GRPB")
    check("opening marks it read", a.get("/chat/api/conversations").get_json()[0]["unread_count"] == 0)
    check("badge back to 0 once the group is opened", a.get("/api/notifications/poll").get_json()["data"]["unread_messages"] == 0)
    with app.app_context():  # administrateur supprimé : le groupe en retrouve un à l'ouverture
        ChatGroupeMembre.query.filter_by(groupe_id=gid, utilisateur_id=ids["a"]).update({"est_admin": False}); db.session.commit()
    check("group without admin gets one on next open", b.get(f"/chat/api/groupe/{gid}").get_json()["groupe"]["membres"] and any(m["est_admin"] for m in b.get(f"/chat/api/groupe/{gid}").get_json()["groupe"]["membres"]))
    with app.app_context():
        ChatGroupeMembre.query.filter_by(groupe_id=gid).update({"est_admin": False}); ChatGroupeMembre.query.filter_by(groupe_id=gid, utilisateur_id=ids["a"]).update({"est_admin": True}); db.session.commit()
    check("group messages are not mixed into private chats", a.get(f"/chat/api/messages/{ids['b']}").get_json()["messages"] == [])
    check("B is not admin", b.get(f"/chat/api/groupe/{gid}").get_json()["groupe"]["is_admin"] is False)

    # --- fichier dans un groupe
    r = a.post("/chat/api/send", data={"groupe_id": gid, "content": "", "file": (io.BytesIO(b"hello"), "note.txt"), "csrf_token": a.tok}, content_type="multipart/form-data")
    fm = r.get_json(); check("file posted in the group", r.status_code == 200 and fm["fichier"]["nom"] == "note.txt", r.status_code)
    with app.app_context():
        m = db.session.get(Message, fm["id"]); stored = os.path.join(app.instance_path, "chat_files", m.fichier_chemin); files_to_clean.append(stored)
    r = c3.get(f"/chat/fichier/{fm['id']}"); check("another member downloads it", r.status_code == 200 and r.data == b"hello"); r.close()
    r = d.get(f"/chat/fichier/{fm['id']}"); check("outsider cannot download it (404)", r.status_code == 404, r.status_code); r.close()

    # --- accès d'un non-membre
    check("outsider cannot open the group (404)", d.get(f"/chat/api/groupe/{gid}").status_code == 404)
    check("outsider cannot post in the group (404)", d.pj("/chat/api/send", {"groupe_id": gid, "content": "intrus"}).status_code == 404)
    check("post to an unknown group refused (404)", a.pj("/chat/api/send", {"groupe_id": "nope", "content": "x"}).status_code == 404)

    # --- droits d'administration
    check("non-admin cannot add members (403)", b.pj(f"/chat/api/groupe/{gid}/membres", {"membres": [ids["d"]]}).status_code == 403)
    check("non-admin cannot rename (403)", b.pj(f"/chat/api/groupe/{gid}/renommer", {"nom": "Piraté"}).status_code == 403)
    check("non-admin cannot remove a member (403)", b.pj(f"/chat/api/groupe/{gid}/retirer", {"user_id": ids["c"]}).status_code == 403)
    check("non-admin cannot delete the group (403)", b.pj(f"/chat/api/groupe/{gid}/supprimer").status_code == 403)
    check("outsider cannot administrate (404)", d.pj(f"/chat/api/groupe/{gid}/membres", {"membres": [ids["d"]]}).status_code == 404)
    r = a.pj(f"/chat/api/groupe/{gid}/renommer", {"nom": "ZZ Equipe 2"}); check("admin renames the group", r.status_code == 200 and b.get(f"/chat/api/groupe/{gid}").get_json()["groupe"]["name"] == "ZZ Equipe 2")
    check("rename with empty name refused", a.pj(f"/chat/api/groupe/{gid}/renommer", {"nom": ""}).status_code == 400)

    # --- ajouter / retirer
    check("adding only existing members refused", a.pj(f"/chat/api/groupe/{gid}/membres", {"membres": [ids["b"]]}).status_code == 400)
    r = a.pj(f"/chat/api/groupe/{gid}/membres", {"membres": [ids["d"]]}); check("admin adds D", r.status_code == 200 and r.get_json()["ajoutes"] == 1)
    check("D now sees the group and its history", len(d.get(f"/chat/api/groupe/{gid}").get_json()["messages"]) == 2)
    check("admin cannot remove themselves via retirer", a.pj(f"/chat/api/groupe/{gid}/retirer", {"user_id": ids["a"]}).status_code == 404)
    check("admin removes D", a.pj(f"/chat/api/groupe/{gid}/retirer", {"user_id": ids["d"]}).status_code == 200)
    check("removed D loses access (404)", d.get(f"/chat/api/groupe/{gid}").status_code == 404 and d.get("/chat/api/conversations").get_json() == [])
    check("page renders with the group UI", all(x in a.get("/chat/").get_data(as_text=True) for x in ("openGroupCreate", 'id="grpPicker"', 'id="grpInfo"')))

    # --- quitter : un nouvel admin est désigné, puis suppression du groupe vide
    check("member B leaves", b.pj(f"/chat/api/groupe/{gid}/quitter").status_code == 200 and b.get(f"/chat/api/groupe/{gid}").status_code == 404)
    check("admin A leaves: group survives", a.pj(f"/chat/api/groupe/{gid}/quitter").status_code == 200)
    with app.app_context():
        ms = ChatGroupeMembre.query.filter_by(groupe_id=gid).all()
        check("C is promoted admin automatically", len(ms) == 1 and ms[0].utilisateur_id == ids["c"] and ms[0].est_admin)
    check("last member leaves: group, messages and file are gone", c3.pj(f"/chat/api/groupe/{gid}/quitter").status_code == 200)
    with app.app_context():
        check("group and messages deleted", db.session.get(ChatGroupe, gid) is None and Message.query.filter_by(groupe_id=gid).count() == 0)
    check("file removed from disk", not os.path.isfile(stored))

    # --- suppression par l'administrateur
    gid2 = a.pj("/chat/api/groupes", {"nom": "ZZ Jetable", "membres": [ids["b"]]}).get_json()["id"]
    r = a.post("/chat/api/send", data={"groupe_id": gid2, "content": "avec fichier", "file": (io.BytesIO(b"zz"), "x.bin"), "csrf_token": a.tok}, content_type="multipart/form-data")
    with app.app_context():
        m = db.session.get(Message, r.get_json()["id"]); stored2 = os.path.join(app.instance_path, "chat_files", m.fichier_chemin); files_to_clean.append(stored2)
    check("admin deletes the group", a.pj(f"/chat/api/groupe/{gid2}/supprimer").status_code == 200)
    with app.app_context():
        check("deleted group: no members, messages or notifications left to read", db.session.get(ChatGroupe, gid2) is None and ChatGroupeMembre.query.filter_by(groupe_id=gid2).count() == 0 and Message.query.filter_by(groupe_id=gid2).count() == 0)
    check("its file was removed from disk", not os.path.isfile(stored2))
    check("member B no longer sees it", b.get("/chat/api/conversations").get_json() == [])
finally:
    with app.app_context():
        for f in files_to_clean:
            if os.path.isfile(f): os.remove(f)
        uid = list(ids.values())
        for g in ChatGroupe.query.filter(ChatGroupe.createur_id.in_(uid)).all(): db.session.delete(g)
        Message.query.filter(Message.sender_id.in_(uid) | Message.receiver_id.in_(uid)).delete(synchronize_session=False)
        Notification.query.filter(Notification.utilisateur_id.in_(uid)).delete(synchronize_session=False)
        db.session.commit()
        for u in Utilisateur.query.filter(Utilisateur.email.in_(list(EM.values()))).all(): db.session.delete(u)
        db.session.commit()
        now = (Message.query.count(), ChatGroupe.query.count(), ChatGroupeMembre.query.count(), Utilisateur.query.count())
        print("cleanup: (messages, groups, members, users)", now, "(was", base, ")")
        results.append(now == base)
print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
