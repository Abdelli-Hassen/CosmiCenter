"""Actions tickets « tous » vs « mes tickets », de bout en bout (vraie base du .env, tout est nettoyé).
- la page Rôles range les cases `_mes` sous « Mes tickets » et les autres sous « Tous les tickets » ;
- un rôle « Tous les tickets + Commenter (mes tickets) » ne peut commenter que ses propres tickets ;
- un rôle « Commenter (tous) » peut commenter n'importe quel ticket visible."""
import os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
import services.email_service as es
es.send_email_notification = lambda *a, **k: None
from models import db, Utilisateur, Role, Permission, Ticket, Commentaire, Notification, HistoriqueTicket

app = create_app("development")
results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())


PW = "T3st-" + secrets.token_urlsafe(8)
E_ADM, E_MES, E_ALL, E_OTH = ("zz.scope.%s@example.invalid" % k for k in ("adm", "mes", "all", "oth"))
ids = {}
with app.app_context():
    base = (Utilisateur.query.count(), Role.query.count(), Ticket.query.count())
    sup = Role.query.filter_by(nom="Super Administrateur").first()
    codes = lambda *c: Permission.query.filter(Permission.code.in_(c)).all()
    r_mes = Role(nom="ZZ Scope Mes", niveau=20, description="t", actif=True)
    r_mes.permissions = codes("tickets.voir_tous", "tickets.commenter_mes")
    r_all = Role(nom="ZZ Scope Tous", niveau=20, description="t", actif=True)
    r_all.permissions = codes("tickets.voir_tous", "tickets.commenter")
    db.session.add_all([r_mes, r_all]); db.session.flush()
    users = {}
    for key, em, rid in (("adm", E_ADM, sup.id), ("mes", E_MES, r_mes.id), ("all", E_ALL, r_all.id), ("oth", E_OTH, r_all.id)):
        u = Utilisateur(nom=key.upper(), prenom="Zz", email=em, role_id=rid)
        u.set_password(PW); db.session.add(u); users[key] = u
    db.session.flush()
    t_mine = Ticket(numero="ZZS1", titre="ZZ mine", description="x", type_ticket="incident", createur_id=users["mes"].id)
    t_other = Ticket(numero="ZZS2", titre="ZZ other", description="x", type_ticket="incident", createur_id=users["oth"].id)
    db.session.add_all([t_mine, t_other]); db.session.commit()
    ids = {"mine": t_mine.id, "other": t_other.id, "r_mes": r_mes.id, "r_all": r_all.id}


def login(email):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": email, "password": PW, "csrf_token": tok("/auth/connexion")})
    return c, tok


def n_comments(tid):
    with app.app_context():
        return Commentaire.query.filter_by(ticket_id=tid).count()


try:
    # 1) page Rôles : rangement des cases
    c, tok = login(E_ADM)
    html = c.get("/admin/roles").get_data(as_text=True)
    blocks = re.split(r'<input type="checkbox" name="permissions" value="[^"]+" class="perm-checkbox perm-page"', html)
    def child_codes(page_code):
        for b in blocks:
            if b.startswith(f' data-perm-id') and f'data-perm-code="{page_code}"' in b.split('>')[0]:
                return set(re.findall(r'perm-action" data-perm-id="[^"]+" data-perm-code="([a-z_.]+)"', b))
        return None
    tous, mes = child_codes("tickets.voir_tous"), child_codes("tickets.voir_mes")
    check("« Tous les tickets » contient les 5 actions sans _mes",
          tous == {"tickets.assigner", "tickets.cloturer", "tickets.commenter", "tickets.modifier", "tickets.supprimer"}, tous)
    check("« Mes tickets » contient les 5 actions _mes",
          mes == {"tickets.assigner_mes", "tickets.cloturer_mes", "tickets.commenter_mes", "tickets.modifier_mes", "tickets.supprimer_mes"}, mes)
    check("aucune action en double entre les deux groupes", tous is not None and mes is not None and not (tous & mes))

    # 2) portée « mes tickets »
    c, tok = login(E_MES)
    tm = tok(f"/tickets/{ids['mine']}")
    c.post(f"/tickets/{ids['mine']}/commenter", data={"contenu": "ZZ ok", "csrf_token": tm})
    check("_mes : commenter son propre ticket -> autorisé", n_comments(ids["mine"]) == 1)
    c.post(f"/tickets/{ids['other']}/commenter", data={"contenu": "ZZ no", "csrf_token": tm})
    check("_mes : commenter le ticket d'un autre -> refusé", n_comments(ids["other"]) == 0)
    page = c.get(f"/tickets/{ids['other']}").get_data(as_text=True)
    check("_mes : pas de zone de réponse sur le ticket d'un autre", "tickets/%s/commenter" % ids["other"] not in page)
    page = c.get(f"/tickets/{ids['mine']}").get_data(as_text=True)
    check("_mes : zone de réponse visible sur son ticket", "tickets/%s/commenter" % ids["mine"] in page)

    # 3) portée « tous »
    c, tok = login(E_ALL)
    c.post(f"/tickets/{ids['other']}/commenter", data={"contenu": "ZZ all", "csrf_token": tok(f"/tickets/{ids['other']}")})
    check("tous : commenter n'importe quel ticket -> autorisé", n_comments(ids["other"]) == 1)
finally:
    with app.app_context():
        for tid in (ids.get("mine"), ids.get("other")):
            if tid:
                Commentaire.query.filter_by(ticket_id=tid).delete()
                HistoriqueTicket.query.filter_by(ticket_id=tid).delete()
                Ticket.query.filter_by(id=tid).delete()
        for em in (E_ADM, E_MES, E_ALL, E_OTH):
            u = Utilisateur.query.filter_by(email=em).first()
            if u:
                Notification.query.filter_by(utilisateur_id=u.id).delete()
                HistoriqueTicket.query.filter_by(utilisateur_id=u.id).delete()
                db.session.delete(u)
        db.session.commit()
        for rid in (ids.get("r_mes"), ids.get("r_all")):
            r = db.session.get(Role, rid) if rid else None
            if r:
                r.permissions = []; db.session.delete(r)
        db.session.commit()
        after = (Utilisateur.query.count(), Role.query.count(), Ticket.query.count())
    check("base restaurée (utilisateurs / rôles / tickets)", after == base, (base, after))
print(f"\n{sum(results)}/{len(results)} checks passed")
sys.exit(0 if all(results) else 1)
