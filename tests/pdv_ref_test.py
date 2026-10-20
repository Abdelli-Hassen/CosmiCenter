import os, re, sys, secrets
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
from app import create_app
from models import db, Utilisateur, Role, PointDeVente, ConfigurationSysteme
from services import referentiels
app = create_app("development")
results = []
def getcfg(k):
    with app.app_context():
        return ConfigurationSysteme.get_valeur(k) or ""
def check(name, cond, extra=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra else ""))

PW = "T3st-" + secrets.token_urlsafe(8); EMAIL = "zz.audit.admin@example.invalid"
with app.app_context():
    role = Role.query.filter_by(nom="Super Administrateur").first()
    u = Utilisateur(nom="AUDIT", prenom="Admin", email=EMAIL, role_id=role.id); u.set_password(PW)
    db.session.add(u); db.session.commit(); uid = u.id
    orig_cats = getcfg("pdv_categories"); orig_themes = getcfg("pdv_themes")
    tables = [r[0] for r in db.session.execute(db.text("select tablename from pg_tables where schemaname='public' and tablename in ('pdv_categories','pdv_themes')"))]
    check("no extra tables exist (pdv_categories / pdv_themes)", tables == [], tables)
pdv_id = None
try:
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": EMAIL, "password": PW, "csrf_token": tok("/auth/connexion")})
    t = tok("/pdv/referentiels")
    html = c.get("/pdv/nouveau").get_data(as_text=True)
    check("form shows DB categories with descriptions", 'class="cat-card-title">Mall<' in html and "Centre commercial" in html)
    check("form shows the DB palette (11 swatches)", html.count('class="color-swatch-btn') == 11, html.count('class="color-swatch-btn'))
    # catégories
    c.post("/pdv/referentiels/categorie", data={"nom": "ZZ-Gare", "description": "Test", "icone": "star", "csrf_token": t})
    check("category added in DB settings", any(x["nom"] == "ZZ-Gare" for x in referentiels.get_all_categories()) if False else 'ZZ-Gare' in getcfg("pdv_categories"))
    check("new category appears at once in the form (cache refreshed)", 'class="cat-card-title">ZZ-Gare<' in c.get("/pdv/nouveau").get_data(as_text=True))
    c.post("/pdv/referentiels/categorie", data={"nom": "zz-gare", "icone": "star", "csrf_token": t})
    check("duplicate (case-insensitive) refused", getcfg("pdv_categories").lower().count('"zz-gare"') == 1)
    c.post("/pdv/referentiels/categorie", data={"nom": "ZZ-Bad", "icone": "<script>", "csrf_token": t})
    check("invalid icon key refused", "ZZ-Bad" not in getcfg("pdv_categories"))
    c.post("/pdv/referentiels/categorie/modifier", data={"nom": "ZZ-Gare", "description": "Modifiee", "icone": "coffee", "ordre": "99", "actif": "on", "csrf_token": t})
    raw = getcfg("pdv_categories")
    check("category edited (description, icon, order)", "Modifiee" in raw and "coffee" in raw)
    c.post("/pdv/referentiels/categorie/modifier", data={"nom": "ZZ-Gare", "description": "x", "icone": "coffee", "ordre": "99", "csrf_token": t})
    check("deactivated category has no card in the form", 'class="cat-card-title">ZZ-Gare<' not in c.get("/pdv/nouveau").get_data(as_text=True))
    # PDV avec catégorie personnalisée
    c.post("/pdv/nouveau", data={"nom": "ZZ-PDV-TEST", "categorie": "custom", "categorie_custom": "ZZ-Rooftop", "csrf_token": t})
    with app.app_context():
        p = PointDeVente.query.filter_by(nom="ZZ-PDV-TEST").first(); pdv_id = p.id if p else None
        check("PDV created", p is not None)
        check("custom category typed in the form is registered in the settings", "ZZ-Rooftop" in getcfg("pdv_categories"))
        check("new PDV default color comes from the DB palette", p and p.couleur == referentiels.get_themes()[0]["couleur"], p.couleur if p else None)
    c.post("/pdv/referentiels/categorie/supprimer", data={"nom": "ZZ-Rooftop", "csrf_token": t})
    check("deleting a category used by a PDV is refused", "ZZ-Rooftop" in getcfg("pdv_categories"))
    # thèmes
    c.post("/pdv/referentiels/theme", data={"nom": "ZZ-Test", "couleur": "#123abc", "csrf_token": t})
    check("theme added", "#123abc" in getcfg("pdv_themes"))
    check("new color shows in the palette of the list page", "#123abc" in c.get("/pdv/").get_data(as_text=True))
    c.post("/pdv/referentiels/theme", data={"nom": "Bad", "couleur": "red;x", "csrf_token": t})
    c.post("/pdv/referentiels/theme", data={"nom": "Dupe", "couleur": "#123ABC", "csrf_token": t})
    raw = getcfg("pdv_themes")
    check("invalid / duplicate colors refused", '"Bad"' not in raw and '"Dupe"' not in raw)
    c.post("/pdv/referentiels/theme/supprimer", data={"couleur": "#123abc", "csrf_token": t})
    check("removed color disappears from the palette", "#123abc" not in c.get("/pdv/").get_data(as_text=True))
    check("anonymous cannot open the admin page", app.test_client().get("/pdv/referentiels").status_code == 302)
    page = c.get("/pdv/referentiels").get_data(as_text=True)
    check("admin page renders with the DB lists", "Palette de thèmes" in page and "Urbain" in page)
finally:
    with app.app_context():
        if pdv_id:
            p = db.session.get(PointDeVente, pdv_id)
            if p: db.session.delete(p)
        ConfigurationSysteme.set_valeur("pdv_categories", orig_cats)
        ConfigurationSysteme.set_valeur("pdv_themes", orig_themes)
        x = db.session.get(Utilisateur, uid)
        if x: db.session.delete(x)
        db.session.commit(); referentiels.invalidate()
        print("cleanup: settings restored =", getcfg("pdv_categories") == orig_cats and getcfg("pdv_themes") == orig_themes, "| PDV count", PointDeVente.query.count())
print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
