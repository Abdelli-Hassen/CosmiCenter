"""
Seed des catégories d'incidents depuis INCIDENT_Catégorie.xlsx
Crée les départements manquants et les 25 catégories d'incidents.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Departement, CategorieTicket

# Départements à créer (uniquement ceux qui n'existent pas encore).
# Les alias permettent de mapper les noms du fichier Excel vers ceux de la BD.
DEPARTEMENTS_NOUVEAUX = [
    {'nom': 'Stock',        'code': 'STK', 'couleur': '#F59E0B', 'description': 'Gestion des stocks et approvisionnements'},
    {'nom': 'Qualité',      'code': 'QUA', 'couleur': '#8B5CF6', 'description': 'Contrôle et assurance qualité'},
    {'nom': 'Maintenance',  'code': 'MAI', 'couleur': '#EF4444', 'description': 'Maintenance et infrastructure'},
    {'nom': 'SI',           'code': 'SI',  'couleur': '#6366F1', 'description': "Système d'information"},
]

# Mapping nom Excel → nom BD (pour les départements qui existent déjà sous un autre nom)
ALIAS_DEPARTEMENTS = {
    'Finance':      'Finances',            # Finances (FIN) existe déjà
    'RH':           'Ressources Humaines', # Ressources Humaines (RH) existe déjà
    'Informatique': 'Support IT',          # Support IT (IT) existe déjà
}

# (nom incident, département Excel, délai_jours, vis-à-vis)
INCIDENTS = [
    ('Produit Manquant',                          'Stock',        1, 'Gestionnaire de Stock'),
    ('Emballage Manquant',                         'Stock',        1, 'Gestionnaire de Stock'),
    ('Feuille de route / Keepsafe manquant',       'Finance',      2, 'Équipe Finance'),
    ('Commande incomplète',                        'Stock',        2, 'Gestionnaire de Stock'),
    ('Retard de livraison',                        'Stock',        1, 'Gestionnaire de Stock'),
    ('Problème de Logistique',                     'Stock',        2, 'Gestionnaire de Stock'),
    ('Réclamations client / produit',              'Qualité',      2, 'Responsable Qualité'),
    ('Produit non conforme',                       'Qualité',      2, 'Responsable Qualité'),
    ('Matériel en panne',                          'Maintenance',  1, 'Responsable Maintenance'),
    ('Manque Matériel',                            'Stock',        1, 'Gestionnaire de Stock'),
    ('Dysfonctionnement plomberie / électricité',  'Maintenance',  1, 'Responsable Maintenance'),
    ('Coupure électricité',                        'Maintenance',  1, 'Responsable Maintenance'),
    ('Coupure eau',                                'Maintenance',  1, 'Responsable Maintenance'),
    ('Facture impayée',                            'Finance',      1, 'Équipe Finance'),
    ('Caisse non fonctionnelle',                   'Maintenance',  1, 'Responsable Maintenance'),
    ('Fausse manipulation paiement en carte',      'Finance',      1, 'Équipe Finance'),
    ('Problème de code caisse',                    'RH',           1, 'Chargé RH'),
    ('Dysfonctionnement des caisses',              'Informatique', 1, 'Équipe IT'),
    ('Erreurs de passation de commande / client',  'Stock',        1, 'Gestionnaire de Stock'),
    ('SI Dysfonctionnel',                          'SI',           1, 'Équipe IT'),
    ('Conflit personnel / client',                 'RH',           1, 'Chargé RH'),
    ('Conflit personnel / personnel',              'RH',           1, 'Chargé RH'),
    ('Incident / Sécurité au travail',             'RH',           1, 'Chargé RH'),
    ('Boîte mail dysfonctionnelle',                'Informatique', 1, 'Équipe IT'),
    ('Wifi dysfonctionnel',                        'Informatique', 1, 'Équipe IT'),
]


def seed_incidents():
    from app import create_app
    app = create_app()

    with app.app_context():
        print('── Départements ──────────────────────────────')

        # Créer les nouveaux départements (si code pas encore pris)
        for d in DEPARTEMENTS_NOUVEAUX:
            existing = Departement.query.filter(
                (Departement.nom == d['nom']) | (Departement.code == d['code'])
            ).first()
            if existing:
                print(f'  [existe] {d["nom"]} ({d["code"]})')
            else:
                dept = Departement(
                    nom=d['nom'],
                    code=d['code'],
                    couleur=d['couleur'],
                    description=d['description'],
                    actif=True,
                )
                db.session.add(dept)
                print(f'  [créé]   {d["nom"]} ({d["code"]})')

        db.session.commit()

        # Construire le mapping nom Excel → objet Departement
        dept_map = {}
        for nom_excel, nom_bd in ALIAS_DEPARTEMENTS.items():
            dept = Departement.query.filter_by(nom=nom_bd).first()
            if dept:
                dept_map[nom_excel] = dept
            else:
                print(f'  [WARN] Département BD introuvable : {nom_bd}')

        for d in DEPARTEMENTS_NOUVEAUX:
            dept = Departement.query.filter_by(nom=d['nom']).first()
            if dept:
                dept_map[d['nom']] = dept

        print(f'\n── Catégories d\'incidents ────────────────────')
        created = skipped = 0
        for nom, dept_nom, delai, vis_a_vis in INCIDENTS:
            dept = dept_map.get(dept_nom)
            if not dept:
                print(f'  [SKIP] Département introuvable : {dept_nom}')
                continue

            existing = CategorieTicket.query.filter_by(nom=nom, departement_id=dept.id).first()
            if existing:
                skipped += 1
                continue

            cat = CategorieTicket(
                nom=nom,
                description=f'Vis-à-vis : {vis_a_vis}',
                type_ticket='incident',
                departement_id=dept.id,
                priorite_defaut='haute' if delai <= 1 else 'moyenne',
                delai_resolution_jours=delai,
                couleur=dept.couleur,
                actif=True,
            )
            db.session.add(cat)
            created += 1
            print(f'  [créé]   {nom} → {dept.nom} ({delai}j)')

        db.session.commit()
        print(f'\n✓ {created} catégorie(s) créée(s), {skipped} déjà existante(s).')


if __name__ == '__main__':
    seed_incidents()
