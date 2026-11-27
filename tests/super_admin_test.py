"""Un utilisateur NON super admin, avec TOUTES les permissions, essaie d'agir sur un Super Administrateur temporaire."""
import os, re, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from models import db, Utilisateur, Role, Permission, PointDeVente, Departement, Entreprise

app = create_app()
users, roles, results = [], [], []


def check(name, ok, info=''):
    results.append(bool(ok))
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f'  {info}'))


try:
    with app.app_context():
        base = (Utilisateur.query.count(), Role.query.count())
        sa_role = Role.query.filter_by(nom='Super Administrateur').first()
        sa_role_id, sa_actif = sa_role.id, sa_role.actif
        strong = Role(nom='ZZ Tout ' + uuid.uuid4().hex[:6], actif=True, systeme=False)
        strong.permissions = Permission.query.all()
        db.session.add(strong); db.session.commit(); roles.append(strong.id)
        pdv = PointDeVente.query.filter_by(actif=True).first().id
        dept = Departement.query.filter_by(actif=True).first().id
        ent = Entreprise.query.filter_by(actif=True).first().id

        def mk(name, **kw):
            u = Utilisateur(nom=name, prenom='ZZSUP', email=f'zz.{uuid.uuid4().hex[:8]}@example.invalid', **kw)
            u.set_password(uuid.uuid4().hex); db.session.add(u); db.session.commit(); users.append(u.id)
            return u.id, u.get_id()

        actor_id, actor_sess = mk('ACTOR', role_id=strong.id, departement_id=dept)
        other_id, other_sess = mk('BOSS', role_id=sa_role.id)
        target, _ = mk('TARGET', role_id=sa_role.id, departement_id=dept, pdv_id=pdv, entreprise_id=ent,
                       anydesk_id='111222333', anydesk_password='zz-secret-ad')

    def client(sess):
        c = app.test_client()
        with c.session_transaction() as s:
            s['_user_id'] = sess; s['_fresh'] = True
        html = c.get('/parametres/profil').get_data(as_text=True)
        c.tok = re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)
        return c

    a, boss = client(actor_sess), client(other_sess)

    def snapshot():
        with app.app_context():
            u = db.session.get(Utilisateur, target)
            if not u:
                return None
            return (u.nom, u.email, u.actif, u.role_id, u.departement_id, u.pdv_id, u.pdv_extra_ids, u.entreprise_id,
                    u.mot_de_passe_hash, u.session_version, u.anydesk_password)

    before = snapshot()
    form = {'nom': 'PIRATE', 'prenom': 'X', 'email': 'zz.pirate@example.invalid', 'password': 'zzzzzzzzzzzz',
            'nouveau_password': 'zzzzzzzzzzzz', 'actif': '0', 'role_id': ''}
    attempts = [
        f'/utilisateurs/{target}/modifier', f'/utilisateurs/{target}/toggle-actif', f'/utilisateurs/{target}/supprimer',
        f'/admin/utilisateurs/{target}/modifier', f'/admin/utilisateurs/{target}/desactiver',
        f'/admin/utilisateurs/{target}/reactiver',
        f'/departements/{dept}/retirer-membre/{target}', f'/pdv/{pdv}/employe/retirer/{target}',
        f'/entreprises/retirer-employe/{target}',
    ]
    with app.app_context():
        rules = [r.rule for r in app.url_map.iter_rules()]
        dept2 = Departement.query.filter(Departement.id != dept).first()
        pdv2 = PointDeVente.query.filter(PointDeVente.id != pdv).first()
        ent2 = Entreprise.query.filter(Entreprise.id != ent).first()
    comp = next(r for r in rules if r.endswith('/<string:id>/assigner-employe')).split('/<')[0]
    attempts[-1] = comp + f'/retirer-employe/{target}'
    adds = [(f'/departements/{(dept2.id if dept2 else dept)}/assigner-membre', {'utilisateur_id': target}),
            (f'/pdv/{(pdv2.id if pdv2 else pdv)}/employe/ajouter', {'utilisateur_id': target}),
            (comp + f'/{(ent2.id if ent2 else ent)}/assigner-employe', {'utilisateur_id': target})]
    for url, data in [(u, form) for u in attempts] + adds:
        r = a.post(url, data=dict(data, csrf_token=a.tok))
        check(f'refused, nothing changed: {url.replace(target, "SA")}', snapshot() == before and r.status_code != 500,
              (r.status_code, snapshot()))

    page = a.get(f'/utilisateurs/{target}').get_data(as_text=True)
    check('profile: no edit / toggle / delete button',
          all(x not in page for x in (f'/utilisateurs/{target}/modifier', 'id="toggleActifBtn"', f'/utilisateurs/{target}/supprimer')))
    check('profile: remote password hidden', 'zz-secret-ad' not in page)
    page = a.get('/utilisateurs/?search=ZZSUP+TARGET').get_data(as_text=True)
    check('directory: no edit / toggle button',
          'ZZSUP TARGET' in page and f'/utilisateurs/{target}/modifier' not in page and f'data-user-id="{target}"' not in page)
    page = a.get('/admin/acces-distance').get_data(as_text=True)
    check('remote access page: no edit link', f'/admin/utilisateurs/{target}/modifier' not in page and 'zz-secret-ad' not in page)
    for url, needle in ((f'/departements/{dept}', f'retirer-membre/{target}'), (f'/pdv/{pdv}', f'employe/retirer/{target}'),
                        (comp + f'/{ent}', f'retirer-employe/{target}')):
        r = a.get(url)
        check(f'no remove button on {url.split("/")[1]} page', r.status_code == 200 and needle not in r.get_data(as_text=True), r.status_code)

    for action in ('supprimer', 'toggle-actif', 'modifier'):
        a.post(f'/admin/roles/{sa_role_id}/{action}', data={'nom': 'ZZ renamed', 'csrf_token': a.tok})
    with app.app_context():
        r = db.session.get(Role, sa_role_id)
        check('Super Administrateur role cannot be renamed, disabled or deleted',
              r is not None and r.nom == 'Super Administrateur' and r.actif == sa_actif)

    page = boss.get('/utilisateurs/?search=ZZSUP+TARGET').get_data(as_text=True)
    check('another Super Administrator still has the buttons', f'/utilisateurs/{target}/modifier' in page)
finally:
    with app.app_context():
        for i in users:
            u = db.session.get(Utilisateur, i)
            if u:
                db.session.delete(u)
        db.session.commit()
        for i in roles:
            r = db.session.get(Role, i)
            if r:
                r.permissions = []
                db.session.delete(r)
        db.session.commit()
        print('cleanup:', (Utilisateur.query.count(), Role.query.count()) == base)
print(f'{sum(results)}/{len(results)} passed')
