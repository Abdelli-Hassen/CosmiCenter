"""Profil : préférence « Sons des notifications » (désactivée = aucun son) et plus de réglage du thème dans le profil.

Autonome : utilisateur `zz.*@example.invalid`, supprimé dans un `finally`.
Lancer : .\\venv\\Scripts\\python.exe tests\\sound_pref_test.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app  # noqa: E402
from models import db, Utilisateur, Role  # noqa: E402

PW = "Passw0rd-zz-123"
EMAIL = "zz.sound@example.invalid"
app = create_app()
results = []


def check(label, ok):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + label)


with app.app_context():
    base = Utilisateur.query.count()
    role = Role.query.filter_by(nom="Super Administrateur").first()
    u = Utilisateur(nom="ZZsound", prenom="T", email=EMAIL, actif=True, role_id=role.id, theme="dark")
    u.set_password(PW)
    db.session.add(u)
    db.session.commit()
    uid = u.id
    check("nouveau compte : sons activés par défaut", u.sons_actifs is True)

try:
    c = app.test_client()
    tok = lambda p: re.search(r'name="csrf-token" content="([^"]+)"', c.get(p).get_data(as_text=True)).group(1)
    c.post("/auth/connexion", data={"email": EMAIL, "password": PW, "csrf_token": tok("/auth/connexion")})

    page = c.get("/parametres/profil").get_data(as_text=True)
    check("profil : case « Sons des notifications » présente et cochée", re.search(r'name="sons_actifs"[^>]*checked', page))
    check("profil : plus de bouton de thème", "themeToggle" not in page and "theme_sombre" not in page)
    check("page : balise chub-sound = 1 quand activé", '<meta name="chub-sound" content="1">' in page)

    def save(**extra):
        data = {"nom": "ZZsound", "prenom": "T", "email": EMAIL, "csrf_token": tok("/parametres/profil")}
        data.update(extra)
        return c.post("/parametres/profil/modifier", data=data)

    r = save()  # case décochée → pas de champ envoyé
    check("enregistrement sans la case : pas de cookie de thème modifié",
          not any("chub_theme" in h for h in r.headers.getlist("Set-Cookie")))
    with app.app_context():
        usr = db.session.get(Utilisateur, uid)
        check("sons désactivés enregistrés", usr.sons_actifs is False)
        check("le thème du compte n'est pas modifié par le profil", usr.theme == "dark")
    page = c.get("/parametres/profil").get_data(as_text=True)
    check("page : balise chub-sound = 0 quand désactivé", '<meta name="chub-sound" content="0">' in page)
    check("profil : case décochée", not re.search(r'name="sons_actifs"[^>]*checked', page))

    save(sons_actifs="on")
    with app.app_context():
        check("sons réactivés enregistrés", db.session.get(Utilisateur, uid).sons_actifs is True)
    check("page : balise chub-sound = 1 après réactivation",
          '<meta name="chub-sound" content="1">' in c.get("/parametres/profil").get_data(as_text=True))

    js = open(os.path.join(ROOT, "static", "js", "sounds.js"), encoding="utf-8").read()
    check("sounds.js : ne joue rien quand la préférence est désactivée",
          "chub-sound" in js and "!enabled()" in js)
finally:
    with app.app_context():
        Utilisateur.query.filter(Utilisateur.email == EMAIL).delete(synchronize_session=False)
        db.session.commit()
        check(f"retour à la base de référence ({base} utilisateurs)", Utilisateur.query.count() == base)

print(f"SUMMARY: {sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
