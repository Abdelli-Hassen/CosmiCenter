"""
Déplace les photos de profil existantes vers static/uploads/profiles/
et met à jour utilisateurs.photo_profil (valeur relative à static/uploads/).
"""
import os
import shutil
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Utilisateur


def migrate():
    from app import create_app
    app = create_app()

    with app.app_context():
        base = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
        if not os.path.isabs(base):
            base = os.path.abspath(base)
        dest = os.path.join(base, 'profiles')
        os.makedirs(dest, exist_ok=True)

        moved = 0
        for u in Utilisateur.query.filter(Utilisateur.photo_profil.isnot(None)).all():
            if u.photo_profil.startswith('profiles/'):
                continue
            src = os.path.join(base, u.photo_profil)
            if os.path.isfile(src):
                shutil.move(src, os.path.join(dest, u.photo_profil))
                u.photo_profil = f'profiles/{u.photo_profil}'
                moved += 1
                print(f'  [déplacé] {u.email} → {u.photo_profil}')
            else:
                print(f'  [introuvable] {u.email} : {u.photo_profil}')
        db.session.commit()
        print(f'\n✓ {moved} photo(s) déplacée(s) vers {dest}')


if __name__ == '__main__':
    migrate()
