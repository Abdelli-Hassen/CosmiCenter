import os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, CategorieConnaissance, ArticleConnaissance, ArticleVue
app = create_app("development")
results = []
def check(name, cond, extra=""):
    results.append(bool(cond)); print((("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else "")).encode("ascii", "replace").decode())

PW = "T3st-" + secrets.token_urlsafe(8)
EM = {"m": "zz.kb.m@example.invalid", "a": "zz.kb.a@example.invalid", "b": "zz.kb.b@example.invalid"}
with app.app_context():
    sup = Role.query.filter_by(nom="Super Administrateur").first()
    reader = Role.query.filter_by(nom="Responsable Point de Vente").first()
    for k, e in EM.items():
        u = Utilisateur(nom="KB" + k.upper(), prenom="Zz", email=e, role_id=(sup.id if k == "m" else reader.id)); u.set_password(PW); db.session.add(u)
    cat = CategorieConnaissance(nom="ZZ cat kb", description="test"); db.session.add(cat); db.session.commit()
    ids = {k: Utilisateur.query.filter_by(email=e).first().id for k, e in EM.items()}
    art = ArticleConnaissance(titre="ZZ article", contenu="contenu", categorie_id=cat.id, auteur_id=ids["m"]); db.session.add(art); db.session.commit()
    aid, cid = art.id, cat.id
    nb_users = Utilisateur.query.count()
try:
    def client(k):
        c = app.test_client()
        tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
        c.post("/auth/connexion", data={"email": EM[k], "password": PW, "csrf_token": tok("/auth/connexion")})
        return c
    m, a, b = client("m"), client("a"), client("b")
    with app.app_context():
        can_read = Utilisateur.query.filter_by(email=EM["a"]).first().has_permission("base_connaissance.voir")
        can_manage = Utilisateur.query.filter_by(email=EM["a"]).first().has_permission("base_connaissance.creer")
    check("test reader can read but not manage the knowledge base", can_read and not can_manage, (can_read, can_manage))
    for _ in range(3): r = a.get(f"/base_connaissance/article/{aid}")
    check("article page opens", r.status_code == 200, r.status_code)
    with app.app_context():
        art = db.session.get(ArticleConnaissance, aid)
        row = ArticleVue.query.filter_by(article_id=aid, utilisateur_id=ids["a"]).first()
        check("3 opens by the same person count as 1 view", art.vues == 1, art.vues)
        check("that person's own counter is 3", row and row.nb_vues == 3, row and row.nb_vues)
    for _ in range(2): b.get(f"/base_connaissance/article/{aid}")
    with app.app_context():
        art = db.session.get(ArticleConnaissance, aid)
        check("a second person raises the views to 2", art.vues == 2, art.vues)
        check("one row per person (2 rows)", ArticleVue.query.filter_by(article_id=aid).count() == 2)
    html = a.get(f"/base_connaissance/article/{aid}").get_data(as_text=True)
    check("plain reader sees the count but no viewers list", "2 lecteurs" in html and "viewers-pop" not in html.split("<body")[1])
    html = m.get(f"/base_connaissance/article/{aid}").get_data(as_text=True)
    check("manager sees the viewers dropdown", "viewers-pop-list" in html)
    # A a ouvert 3 fois + 1 (contrôle de la page) = 4 ; B 2 ; le gestionnaire lui-même 1 (sa propre ouverture compte aussi)
    check("dropdown shows each person with their count", "KBA" in html and sorted(re.findall(r"(\d+) fois", html)) == ["1", "2", "4"], re.findall(r"\d+ fois", html))
    html = m.get(f"/base_connaissance/categorie/{cid}").get_data(as_text=True)
    check("category list: manager dropdown too", "viewers-pop-list" in html and "4 fois" in html)
    html = b.get(f"/base_connaissance/categorie/{cid}").get_data(as_text=True)
    check("category list: plain reader has no dropdown", "viewers-pop-list" not in html)
finally:
    with app.app_context():
        ArticleVue.query.filter_by(article_id=aid).delete()
        ArticleConnaissance.query.filter_by(id=aid).delete()
        CategorieConnaissance.query.filter_by(id=cid).delete()
        db.session.commit()
        for e in EM.values():
            u = Utilisateur.query.filter_by(email=e).first()
            if u: db.session.delete(u)
        db.session.commit()
        print("cleanup done | users:", Utilisateur.query.count(), "| views rows:", ArticleVue.query.count())
print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
