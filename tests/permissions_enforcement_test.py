"""Chaque permission décide réellement de ce qu'elle annonce (plus aucun niveau, aucun droit implicite).

Rôles / utilisateurs / tickets / PDV temporaires `ZZ…`, tout est supprimé dans le `finally`.
Lancer : venv\\Scripts\\python.exe tests\\permissions_enforcement_test.py   (jamais sur une base de production)
"""
import os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
import services.email_service as es
es.send_email_notification = lambda *a, **k: None
from models import (db, Utilisateur, Role, Permission, Ticket, Commentaire, Departement, PointDeVente, Entreprise,
                    HistoriqueTicket, Notification, SUPER_ADMIN_ROLE)

app = create_app("development")
results = []


def check(name, cond, extra=""):
    results.append(bool(cond))
    print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())


PW = "T3st-" + secrets.token_urlsafe(8)
ok = lambda r: r.status_code == 200
no = lambda r: r.status_code in (302, 403)
mail = lambda tag: f"zz.enf.{tag}@example.invalid"
made_roles, made_users, made_tickets, made_pdv, made_ent, made_dept = [], [], [], [], [], []

with app.app_context():
    base = (Utilisateur.query.count(), Role.query.count(), Ticket.query.count(), PointDeVente.query.count(),
            Entreprise.query.count(), Departement.query.count(), Permission.query.count())
    sa = Role.query.filter_by(nom=SUPER_ADMIN_ROLE).first()
    sa_id = sa.id
    sa_perm_ids_before = sorted(p.id for p in sa.permissions)
    n_perms_total = Permission.query.count()
    check("le rôle Super Administrateur a TOUTES les permissions cochées (plus d'implicite)", len(sa_perm_ids_before) == n_perms_total, f"{len(sa_perm_ids_before)}/{n_perms_total}")

    def mkrole(tag, *codes, niveau=0):
        r = Role(nom=f"ZZ Enf {tag}", niveau=niveau, description="t", actif=True)
        r.permissions = Permission.query.filter(Permission.code.in_(codes)).all() if codes else []
        db.session.add(r); db.session.flush(); made_roles.append(r.id)
        return r

    d1 = Departement(nom="ZZ-ENF-D1", code="ZZE1", sla_resolution_heures=24)
    d2 = Departement(nom="ZZ-ENF-D2", code="ZZE2", sla_resolution_heures=24)
    db.session.add_all([d1, d2]); db.session.flush(); made_dept += [d1.id, d2.id]
    D1, D2 = d1.id, d2.id

    def mkuser(tag, role, dept=None):
        u = Utilisateur(nom="ENF", prenom=tag, email=mail(tag), role_id=role.id, departement_id=dept)
        u.set_password(PW); db.session.add(u); db.session.flush(); made_users.append(u.id)
        return u

    # --- rôles de test
    r_none = mkrole("none")                                   # aucune permission
    r_lvl100 = mkrole("lvl100", niveau=100)                    # « niveau 100 » mais aucune case : ne doit RIEN pouvoir
    r_creer = mkrole("creer", "tickets.creer")
    r_vmes = mkrole("vmes", "tickets.voir_mes")
    r_vtous = mkrole("vtous", "tickets.voir_tous")
    r_dash = mkrole("dash", "dashboard.voir")
    r_dept = mkrole("dept", "departements.voir")
    r_uvoir = mkrole("uvoir", "utilisateurs.voir")
    r_uvtous = mkrole("uvtous", "utilisateurs.voir", "utilisateurs.voir_tous")
    r_ent = mkrole("ent", "entreprises.voir")
    r_adash = mkrole("adash", "admin_dashboard.voir")
    r_arv = mkrole("arv", "admin_roles.voir")
    r_arm = mkrole("arm", "admin_roles.voir", "admin_roles.modifier")
    r_clo = mkrole("clo", "tickets.voir_mes", "tickets.cloturer_mes")
    r_mod = mkrole("mod", "tickets.voir_mes", "tickets.modifier_mes")
    r_delm = mkrole("delm", "tickets.voir_mes", "tickets.supprimer_mes")
    r_dela = mkrole("dela", "tickets.voir_tous", "tickets.supprimer")
    r_pdv = mkrole("pdv", "pdv.voir")
    r_pdvd = mkrole("pdvd", "pdv.voir", "pdv.supprimer")
    r_ugest = mkrole("ugest", "utilisateurs.voir", "utilisateurs.voir_tous", "utilisateurs.modifier", "utilisateurs.activer",
                     "utilisateurs.supprimer", "utilisateurs.creer")

    R_LVL100, R_NONE = r_lvl100.id, r_none.id
    U = {}
    for tag, role, dept in (("none", r_none, D1), ("lvl100", r_lvl100, D1), ("creer", r_creer, D1), ("vmes", r_vmes, D1),
                            ("vtous", r_vtous, D1), ("dash", r_dash, D1), ("dept", r_dept, D1), ("uvoir", r_uvoir, D1),
                            ("uvtous", r_uvtous, D1), ("ent", r_ent, D1), ("adash", r_adash, D1), ("arv", r_arv, D1),
                            ("arm", r_arm, D1), ("clo", r_clo, D1), ("mod", r_mod, D1), ("delm", r_delm, D1),
                            ("dela", r_dela, D2), ("pdv", r_pdv, D1), ("pdvd", r_pdvd, D1), ("ugest", r_ugest, D1),
                            ("target1", r_none, D1), ("target2", r_none, D2)):
        U[tag] = mkuser(tag, role, dept).id
    sa_user = mkuser("sa", sa, D1); U["sa"] = sa_user.id
    sa_target = mkuser("satarget", sa, D1); U["satarget"] = sa_target.id

    def mkticket(num, creator, dept):
        t = Ticket(numero=num, titre=f"ZZ {num}", description="t", createur_id=creator, departement_id=dept,
                   statut="nouveau", priorite="moyenne", type_ticket="incident")
        db.session.add(t); db.session.flush(); made_tickets.append(t.id)
        return t.id

    T_creator_none = mkticket("ZZE1", U["none"], D1)       # créé par « none » : droits seulement via permissions
    T_clo = mkticket("ZZE2", U["clo"], D1)
    T_mod = mkticket("ZZE3", U["mod"], D1)
    T_delm_in = mkticket("ZZE4", U["delm"], D1)
    T_delm_out = mkticket("ZZE5", U["target2"], D2)        # hors de portée de « delm »
    T_dela_any = mkticket("ZZE6", U["target1"], D1)
    pdv_free = PointDeVente(nom="ZZ-ENF-PDV-LIBRE"); pdv_busy = PointDeVente(nom="ZZ-ENF-PDV-OCCUPE")
    db.session.add_all([pdv_free, pdv_busy]); db.session.flush(); made_pdv += [pdv_free.id, pdv_busy.id]
    PDV_FREE, PDV_BUSY = pdv_free.id, pdv_busy.id
    U["staff"] = mkuser("staff", r_none, D1).id
    db.session.get(Utilisateur, U["staff"]).pdv_id = PDV_BUSY
    ent = Entreprise(nom="ZZ-ENF-ENT", type_entreprise="externe"); db.session.add(ent); db.session.flush(); made_ent.append(ent.id)
    ENT = ent.id
    # un utilisateur avec des données liées (commentaire) -> suppression refusée
    U["linked"] = mkuser("linked", r_none, D1).id
    U["delme"] = mkuser("delme", r_none, D1).id   # aucune donnée liée : supprimable
    db.session.add(Commentaire(ticket_id=T_creator_none, auteur_id=U["linked"], contenu="zz"))
    db.session.commit()

SA_TOKEN_NOTE = None


def client(tag):
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": mail(tag), "password": PW, "csrf_token": tok("/auth/connexion")})
    c.tok = lambda: tok("/parametres/profil")
    return c


def ticket_state(tid):
    with app.app_context():
        t = db.session.get(Ticket, tid)
        return None if t is None else t.statut


try:
    # ───────────────────────── A. plus aucun niveau ─────────────────────────
    with app.app_context():
        role100 = db.session.get(Role, R_LVL100)
        check("un rôle de niveau 100 SANS case cochée n'a aucune permission", not role100.has_permission("tickets.creer") and not role100.has_permission("admin_roles.modifier"))
    c = client("lvl100")
    check("niveau 100 sans case : /admin/tableau-bord refusé", no(c.get("/admin/tableau-bord")))
    check("niveau 100 sans case : /admin/roles refusé", no(c.get("/admin/roles")))
    check("niveau 100 sans case : /tickets/nouveau refusé", no(c.get("/tickets/nouveau")))

    # ───────────────────────── A2. la page Rôles dessine TOUTES les permissions ─────────────────────────
    # (une permission non dessinée serait supprimée en silence à chaque enregistrement d'un rôle)
    html = client("sa").get("/admin/roles").get_data(as_text=True)
    with app.app_context():
        missing = [p.code for p in Permission.query.all() if f'value="{p.id}"' not in html]
    check("la page Rôles affiche une case pour chacune des permissions", not missing, missing)

    # ───────────────────────── B. permissions « menu seul » désormais appliquées ─────────────────────────
    cn = client("none")
    cases = [
        ("tickets.creer", "creer", "/tickets/nouveau"),
        ("tickets.voir_mes", "vmes", "/tickets/mes-tickets"),
        ("tickets.voir_tous", "vtous", "/tickets/liste"),
        ("dashboard.voir", "dash", "/tickets/tableau-bord"),
        ("departements.voir", "dept", "/departements/"),
        ("utilisateurs.voir", "uvoir", "/utilisateurs/"),
        ("admin_dashboard.voir", "adash", "/admin/tableau-bord"),
        ("admin_roles.voir", "arv", "/admin/roles"),
    ]
    for code, tag, url in cases:
        check(f"{code}: sans la case, {url} refusé", no(cn.get(url)))
        check(f"{code}: avec la case, {url} s'ouvre", ok(client(tag).get(url)), client(tag).get(url).status_code)
    check("departements.voir: la fiche d'un département est aussi protégée", no(cn.get(f"/departements/{D1}")) and ok(client("dept").get(f"/departements/{D1}")))
    r = cn.get("/tickets/tableau-bord", follow_redirects=True)
    check("sans dashboard.voir : refus puis retour sur le profil (aucune boucle)", ok(r) and r.request.path == "/parametres/profil", r.request.path)
    check("la page d'accueil d'un rôle sans tableau de bord est son profil", cn.get("/", follow_redirects=True).request.path == "/parametres/profil")

    # entreprises.voir : détail + JSON
    check("entreprises.voir: détail refusé sans la case", no(cn.get(f"/companies/{ENT}")))
    check("entreprises.voir: JSON refusé sans la case", cn.get(f"/companies/{ENT}/json").status_code in (302, 403))
    ce = client("ent")
    check("entreprises.voir: détail et JSON ouverts avec la case", ok(ce.get(f"/companies/{ENT}")) and ok(ce.get(f"/companies/{ENT}/json")))

    # ───────────────────────── C. profils : utilisateurs.voir + utilisateurs.voir_tous ─────────────────────────
    check("son propre profil est toujours accessible (sans aucune case)", ok(cn.get(f"/utilisateurs/{U['none']}")))
    check("le profil d'un autre est refusé sans utilisateurs.voir", no(cn.get(f"/utilisateurs/{U['target1']}")))
    cv = client("uvoir")
    check("avec utilisateurs.voir : profil d'un collègue du même département ouvert", ok(cv.get(f"/utilisateurs/{U['target1']}")))
    check("avec utilisateurs.voir seul : profil d'un autre département refusé", no(cv.get(f"/utilisateurs/{U['target2']}")))
    check("avec utilisateurs.voir_tous : profil d'un autre département ouvert", ok(client("uvtous").get(f"/utilisateurs/{U['target2']}")))

    # ───────────────────────── D. admin_roles.modifier ─────────────────────────
    def post_role(tag, nom):
        c = client(tag)
        return c.post("/admin/roles/creer", data={"nom": nom, "description": "t", "couleur": "#112233", "csrf_token": c.tok()})
    def role_exists(nom):
        with app.app_context():
            r = Role.query.filter_by(nom=nom).first()
            if r and r.id not in made_roles:
                made_roles.append(r.id)
            return r is not None
    post_role("arv", "ZZ Enf cree-par-voir"); check("admin_roles.voir seul : création de rôle refusée", not role_exists("ZZ Enf cree-par-voir"))
    post_role("lvl100", "ZZ Enf cree-par-100"); check("niveau 100 sans case : création de rôle refusée", not role_exists("ZZ Enf cree-par-100"))
    post_role("arm", "ZZ Enf cree-par-modifier"); check("admin_roles.modifier : création de rôle acceptée", role_exists("ZZ Enf cree-par-modifier"))

    # ───────────────────────── E. Super Administrateur protégé ─────────────────────────
    cg = client("ugest")
    cg.post(f"/utilisateurs/{U['satarget']}/modifier", data={"nom": "HACK", "prenom": "X", "email": mail("satarget"), "csrf_token": cg.tok()})
    with app.app_context():
        check("un non Super Admin ne peut pas modifier un compte Super Admin", db.session.get(Utilisateur, U["satarget"]).nom == "ENF")
    cg.post(f"/utilisateurs/{U['satarget']}/toggle-actif", data={"csrf_token": cg.tok()})
    with app.app_context():
        check("ni le désactiver", db.session.get(Utilisateur, U["satarget"]).actif is True)
    cg.post(f"/utilisateurs/{U['satarget']}/supprimer", data={"csrf_token": cg.tok()})
    with app.app_context():
        check("ni le supprimer", db.session.get(Utilisateur, U["satarget"]) is not None)
    cg.post(f"/utilisateurs/{U['target1']}/modifier", data={"nom": "ENF", "prenom": "target1", "email": mail("target1"), "role_id": sa_id, "csrf_token": cg.tok()})
    with app.app_context():
        check("ni s'attribuer / attribuer le rôle Super Administrateur", db.session.get(Utilisateur, U["target1"]).role_id != sa_id)
    csa = client("sa")
    csa.post(f"/utilisateurs/{U['target1']}/modifier", data={"nom": "ENF", "prenom": "target1", "email": mail("target1"), "role_id": sa_id, "csrf_token": csa.tok()})
    with app.app_context():
        got = db.session.get(Utilisateur, U["target1"])
        check("un Super Admin peut attribuer le rôle Super Administrateur", got.role_id == sa_id)
        got.role_id = R_NONE; db.session.commit()

    # suppression d'un utilisateur : bouton, refus détaillé, succès
    page = cg.get(f"/utilisateurs/{U['delme']}").get_data(as_text=True)
    check("utilisateurs.supprimer : le bouton Supprimer existe sur la fiche", f"/utilisateurs/{U['delme']}/supprimer" in page)
    check("sans la case, pas de bouton Supprimer", "/supprimer" not in client("uvtous").get(f"/utilisateurs/{U['delme']}").get_data(as_text=True))
    r = cg.post(f"/utilisateurs/{U['linked']}/supprimer", data={"csrf_token": cg.tok()}, follow_redirects=True)
    with app.app_context():
        still = db.session.get(Utilisateur, U["linked"]) is not None
    txt = r.get_data(as_text=True)
    check("compte avec données liées : suppression refusée, avec le détail", still and "Suppression impossible" in txt, (still, "Suppression impossible" in txt))
    cg.post(f"/utilisateurs/{U['delme']}/supprimer", data={"csrf_token": cg.tok()})
    with app.app_context():
        gone = db.session.get(Utilisateur, U["delme"]) is None
    check("compte sans données liées : supprimé", gone)
    if gone:
        made_users.remove(U["delme"])
    cl = client("uvtous")
    cl.post(f"/utilisateurs/{U['target2']}/supprimer", data={"csrf_token": cl.tok()})
    with app.app_context():
        check("sans utilisateurs.supprimer : suppression refusée", db.session.get(Utilisateur, U["target2"]) is not None)

    # garde-fou du rôle Super Administrateur (restauré dans le finally)
    with app.app_context():
        all_but = [p.id for p in Permission.query.all() if p.code != "admin_roles.modifier"]
    r = csa.post(f"/admin/roles/{sa_id}/permissions", data={"permissions": all_but, "csrf_token": csa.tok()}, follow_redirects=True)
    with app.app_context():
        check("le rôle Super Admin ne peut pas perdre admin_roles.modifier (anti-verrouillage)",
              any(p.code == "admin_roles.modifier" for p in db.session.get(Role, sa_id).permissions))
    c_arm = client("arm")
    with app.app_context():
        all_ids = [p.id for p in Permission.query.all()]
    c_arm.post(f"/admin/roles/{sa_id}/permissions", data={"permissions": all_ids[:3], "csrf_token": c_arm.tok()})
    with app.app_context():
        check("un non Super Admin ne peut pas modifier les permissions du rôle Super Admin", len(db.session.get(Role, sa_id).permissions) == n_perms_total)

    # ───────────────────────── F. tickets : modifier / clôturer / supprimer ─────────────────────────
    c_cr = client("none")  # créateur de T_creator_none, sans aucune permission
    check("créateur sans permission : ne peut plus modifier son ticket (page refusée)", no(c_cr.get(f"/tickets/{T_creator_none}/modifier")))
    c_cr.post(f"/tickets/{T_creator_none}/statut", data={"statut": "en_cours", "csrf_token": c_cr.tok()})
    check("créateur sans permission : ne peut pas changer le statut", ticket_state(T_creator_none) == "nouveau")
    c_cr.post(f"/tickets/{T_creator_none}/fermer", data={"csrf_token": c_cr.tok()})
    check("créateur sans permission : ne peut pas fermer", ticket_state(T_creator_none) == "nouveau")
    c_cr.post(f"/tickets/{T_creator_none}/supprimer", data={"csrf_token": c_cr.tok()})
    check("créateur sans permission : ne peut pas supprimer", ticket_state(T_creator_none) == "nouveau")

    cc = client("clo")      # cloturer_mes seulement
    cc.post(f"/tickets/{T_clo}/statut", data={"statut": "en_cours", "csrf_token": cc.tok()})
    check("cloturer_mes seul : ne peut pas passer en « en cours » (c'est tickets.modifier)", ticket_state(T_clo) == "nouveau")
    check("cloturer_mes seul : ne peut pas ouvrir la page Modifier", no(cc.get(f"/tickets/{T_clo}/modifier")))
    cc.post(f"/tickets/{T_clo}/fermer", data={"csrf_token": cc.tok()})
    check("cloturer_mes : peut fermer", ticket_state(T_clo) == "ferme")
    cc.post(f"/tickets/{T_clo}/reouvrir", data={"csrf_token": cc.tok()})
    check("cloturer_mes : peut rouvrir", ticket_state(T_clo) == "en_cours")

    cm = client("mod")      # modifier_mes seulement
    check("modifier_mes : la page Modifier s'ouvre", ok(cm.get(f"/tickets/{T_mod}/modifier")))
    cm.post(f"/tickets/{T_mod}/statut", data={"statut": "en_cours", "csrf_token": cm.tok()})
    check("modifier_mes : peut passer en « en cours »", ticket_state(T_mod) == "en_cours")
    cm.post(f"/tickets/{T_mod}/fermer", data={"csrf_token": cm.tok()})
    check("modifier_mes seul : ne peut pas fermer (c'est tickets.cloturer)", ticket_state(T_mod) == "en_cours")
    cm.post(f"/tickets/{T_mod}/statut", data={"statut": "resolu", "csrf_token": cm.tok()})
    check("modifier_mes seul : ne peut pas résoudre", ticket_state(T_mod) == "en_cours")

    cd = client("delm")     # supprimer_mes
    page = cd.get(f"/tickets/{T_delm_in}").get_data(as_text=True)
    check("supprimer_mes : le bouton Supprimer apparaît sur mon ticket", f"/tickets/{T_delm_in}/supprimer" in page)
    cd.post(f"/tickets/{T_delm_out}/supprimer", data={"csrf_token": cd.tok()})
    check("supprimer_mes : un ticket hors de ma portée n'est pas supprimé", ticket_state(T_delm_out) == "nouveau")
    cd.post(f"/tickets/{T_delm_in}/supprimer", data={"csrf_token": cd.tok()})
    check("supprimer_mes : mon ticket est supprimé", ticket_state(T_delm_in) is None)
    made_tickets.remove(T_delm_in)
    ca = client("dela")     # supprimer (tous)
    ca.post(f"/tickets/{T_dela_any}/supprimer", data={"csrf_token": ca.tok()})
    check("supprimer (tous) : supprime n'importe quel ticket", ticket_state(T_dela_any) is None)
    made_tickets.remove(T_dela_any)
    with app.app_context():
        left = Commentaire.query.filter_by(ticket_id=T_dela_any).count()
    check("la suppression emporte aussi ses commentaires / historique", left == 0)

    # ───────────────────────── G. points de vente ─────────────────────────
    cp = client("pdv")
    cp.post(f"/pdv/{PDV_FREE}/supprimer", data={"csrf_token": cp.tok()})
    with app.app_context():
        check("pdv.supprimer : refusé sans la case", db.session.get(PointDeVente, PDV_FREE) is not None)
    check("pdv.supprimer : bouton visible seulement avec la case", "/supprimer" not in cp.get(f"/pdv/{PDV_FREE}").get_data(as_text=True)
          and f"/pdv/{PDV_FREE}/supprimer" in client("pdvd").get(f"/pdv/{PDV_FREE}").get_data(as_text=True))
    cpd = client("pdvd")
    r = cpd.post(f"/pdv/{PDV_BUSY}/supprimer", data={"csrf_token": cpd.tok()}, follow_redirects=True)
    with app.app_context():
        check("PDV qui a encore du personnel : suppression refusée avec explication",
              db.session.get(PointDeVente, PDV_BUSY) is not None and "Suppression impossible" in r.get_data(as_text=True))
    cpd.post(f"/pdv/{PDV_FREE}/supprimer", data={"csrf_token": cpd.tok()})
    with app.app_context():
        check("PDV libre : supprimé", db.session.get(PointDeVente, PDV_FREE) is None)
    made_pdv.remove(PDV_FREE)
finally:
    with app.app_context():
        sa = db.session.get(Role, sa_id)
        sa.permissions = Permission.query.filter(Permission.id.in_(sa_perm_ids_before)).all()   # restaure le rôle racine
        db.session.commit()
        for tid in made_tickets:
            t = db.session.get(Ticket, tid)
            if t: db.session.delete(t)
        db.session.flush()
        Commentaire.query.filter(Commentaire.auteur_id.in_(made_users)).delete(synchronize_session=False)
        HistoriqueTicket.query.filter(HistoriqueTicket.utilisateur_id.in_(made_users)).delete(synchronize_session=False)
        Notification.query.filter(Notification.utilisateur_id.in_(made_users)).delete(synchronize_session=False)
        for uid in made_users:
            u = db.session.get(Utilisateur, uid)
            if u: db.session.delete(u)
        db.session.flush()
        for nom_like in ("ZZ Enf %",):
            for r in Role.query.filter(Role.nom.like(nom_like)).all():
                r.permissions.clear(); db.session.delete(r)
        for pid in made_pdv:
            p = db.session.get(PointDeVente, pid)
            if p: db.session.delete(p)
        for eid in made_ent:
            e = db.session.get(Entreprise, eid)
            if e: db.session.delete(e)
        for did in made_dept:
            d = db.session.get(Departement, did)
            if d: db.session.delete(d)
        db.session.commit()
        after = (Utilisateur.query.count(), Role.query.count(), Ticket.query.count(), PointDeVente.query.count(),
                 Entreprise.query.count(), Departement.query.count(), Permission.query.count())
        sa_after = sorted(p.id for p in db.session.get(Role, sa_id).permissions)
    check("base restaurée (utilisateurs / rôles / tickets / PDV / entreprises / départements / permissions)", after == base, f"{base} -> {after}")
    check("permissions du rôle Super Administrateur restaurées", sa_after == sa_perm_ids_before)
    print(f"\n{sum(results)}/{len(results)} checks passed")

if not all(results):
    sys.exit(1)
