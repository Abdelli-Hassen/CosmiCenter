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
]

# Mapping nom Excel → nom BD (pour les départements qui existent déjà sous un autre nom)
ALIAS_DEPARTEMENTS = {
    'Finance':      'Finances',            # Finances (FIN) existe déjà
    'RH':           'Ressources Humaines', # Ressources Humaines (RH) existe déjà
}

# Tout ce qui touche à la technologie (SI, Informatique...) appartient au département IT (code 'IT')
CODE_IT = 'IT'
NOMS_EXCEL_IT = ('Informatique', 'SI')

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
    ('Caisse non fonctionnelle',                   'Informatique', 1, 'Équipe IT'),
    ('Fausse manipulation paiement en carte',      'Finance',      1, 'Équipe Finance'),
    ('Problème de code caisse',                    'Informatique', 1, 'Équipe IT'),
    ('Dysfonctionnement des caisses',              'Informatique', 1, 'Équipe IT'),
    ('Erreurs de passation de commande / client',  'Stock',        1, 'Gestionnaire de Stock'),
    ('SI Dysfonctionnel',                          'SI',           1, 'Équipe IT'),
    ('Conflit personnel / client',                 'RH',           1, 'Chargé RH'),
    ('Conflit personnel / personnel',              'RH',           1, 'Chargé RH'),
    ('Incident / Sécurité au travail',             'RH',           1, 'Chargé RH'),
    ('Boîte mail dysfonctionnelle',                'Informatique', 1, 'Équipe IT'),
    ('Wifi dysfonctionnel',                        'Informatique', 1, 'Équipe IT'),
]

# Second tableau (par département) : (nom, département Excel, type, délai_jours, vis-à-vis)
# I = incident, D = demande
PAR_DEPARTEMENT = [
    # RH
    ('Problème lié au comportement (collègue, client...)', 'RH', 'incident', 1, 'Chargé RH'),
    ('Demande attestation de travail',   'RH', 'demande', 2, 'Chargé RH'),
    ('Demande attestation de salaire',   'RH', 'demande', 2, 'Chargé RH'),
    ('Demande fiche de paie',            'RH', 'demande', 2, 'Chargé RH'),
    # Maintenance
    ('Problème SI (OPOZ, outil de ticketing, système fidélité...)', 'Informatique', 'incident', 1, 'Équipe IT'),
    ('Équipement défectueux (machine à cafés, moulin, frigo, etc.)', 'Maintenance', 'incident', 1, 'Responsable Maintenance'),
    ('Électricité (coupure, lampe défectueuse...)', 'Maintenance', 'incident', 1, 'Responsable Maintenance'),
    ('Plomberie',                        'Maintenance', 'incident', 1, 'Responsable Maintenance'),
    ('Climatisation',                    'Maintenance', 'incident', 1, 'Responsable Maintenance'),
    ('Problème Caisse',                  'Informatique', 'incident', 1, 'Équipe IT'),
    ('Problème WIFI',                    'Informatique', 'incident', 1, 'Équipe IT'),
    ('Réclamation code caisse',          'Informatique', 'incident', 1, 'Équipe IT'),
    ('Besoins équipements',              'Maintenance', 'demande',  2, 'Responsable Maintenance'),
    # Qualité
    ('Réclamation client',               'Qualité', 'incident', 2, 'Responsable Qualité'),
    ('Réclamation non conformité produit', 'Qualité', 'incident', 2, 'Responsable Qualité'),
    ('Accident de travail',              'Qualité', 'incident', 1, 'Responsable Qualité'),
    ('Inspection autorité',              'Qualité', 'incident', 1, 'Responsable Qualité'),
    ('Besoins fiches de suivi qualité',  'Qualité', 'demande',  2, 'Responsable Qualité'),
    ('Besoins fiches techniques produits', 'Qualité', 'demande', 2, 'Responsable Qualité'),
    # Finance
    ('Feuille de route & keep safe manquants', 'Finance', 'demande', 2, 'Équipe Finance'),
    ('Enveloppes manquantes',            'Finance', 'demande',  2, 'Équipe Finance'),
    ('Problème TPE',                     'Informatique', 'incident', 1, 'Équipe IT'),
    # Stock
    ('Besoins Produits Food & boissons', 'Stock', 'demande',  2, 'Gestionnaire de Stock'),
    ('Besoins Emballages',               'Stock', 'demande',  2, 'Gestionnaire de Stock'),
    ('Besoins factures/BL',              'Stock', 'demande',  2, 'Gestionnaire de Stock'),
    ("Besoins Produits d'hygiène",       'Stock', 'demande',  2, 'Gestionnaire de Stock'),
    ('Non conformité réception marchandises', 'Stock', 'incident', 1, 'Gestionnaire de Stock'),
]

TOUTES = [(n, d, 'incident', j, v) for (n, d, j, v) in INCIDENTS] + PAR_DEPARTEMENT



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

        # Département IT (SI + Informatique)
        it_dept = Departement.query.filter_by(code=CODE_IT).first()
        if it_dept:
            for n in NOMS_EXCEL_IT:
                dept_map[n] = it_dept

            # Nettoyage : l'ancien département 'SI' n'existe pas → on déplace ses catégories vers IT
            si_dept = Departement.query.filter(Departement.code == 'SI', Departement.id != it_dept.id).first()
            if si_dept:
                for cat in list(si_dept.categories):
                    cat.departement_id = it_dept.id
                if not si_dept.membres:
                    db.session.delete(si_dept)
                    print('  [supprimé] ancien département SI (catégories déplacées vers IT)')
                else:
                    si_dept.actif = False
                    print('  [désactivé] ancien département SI (a des membres)')
            # Catégories techniques déjà créées dans un autre département → déplacées vers IT
            noms_it = [n for (n, d, *_r) in TOUTES if d in NOMS_EXCEL_IT]
            for cat in CategorieTicket.query.filter(
                    CategorieTicket.nom.in_(noms_it),
                    CategorieTicket.departement_id != it_dept.id).all():
                print(f'  [déplacé]  {cat.nom} → {it_dept.nom}')
                cat.departement_id = it_dept.id
            db.session.commit()
        else:
            print(f"  [WARN] Département IT (code '{CODE_IT}') introuvable")

        print(f'\n── Catégories d\'incidents ────────────────────')
        created = skipped = 0
        for nom, dept_nom, type_t, delai, vis_a_vis in TOUTES:
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
                type_ticket=type_t,
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
