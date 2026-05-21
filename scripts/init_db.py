"""
Script d'initialisation de la base de données CosmittoDesk 2.0
Crée les tables, les permissions, les rôles et un utilisateur administrateur par défaut
"""
import sys
import os

# Ajouter le dossier parent au path pour pouvoir importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Permission, Role, Utilisateur, Departement
from datetime import datetime


def initialiser_permissions():
    """Créer toutes les permissions système"""
    permissions_data = [
        # Tickets
        {'code': 'tickets.creer', 'nom': 'Créer des tickets', 'categorie': 'tickets'},
        {'code': 'tickets.voir_tous', 'nom': 'Voir tous les tickets', 'categorie': 'tickets'},
        {'code': 'tickets.modifier', 'nom': 'Modifier les tickets', 'categorie': 'tickets'},
        {'code': 'tickets.supprimer', 'nom': 'Supprimer les tickets', 'categorie': 'tickets'},
        {'code': 'tickets.assigner', 'nom': 'Assigner les tickets', 'categorie': 'tickets'},
        {'code': 'tickets.fermer', 'nom': 'Fermer les tickets', 'categorie': 'tickets'},
        
        # Utilisateurs
        {'code': 'admin.utilisateurs', 'nom': 'Gérer les utilisateurs', 'categorie': 'admin'},
        {'code': 'utilisateurs.voir', 'nom': 'Voir les utilisateurs', 'categorie': 'utilisateurs'},
        
        # Départements
        {'code': 'admin.departements', 'nom': 'Gérer les départements', 'categorie': 'admin'},
        {'code': 'departements.voir', 'nom': 'Voir les départements', 'categorie': 'departements'},
        
        # Catégories
        {'code': 'admin.categories', 'nom': 'Gérer les catégories', 'categorie': 'admin'},
        
        # Rôles
        {'code': 'admin.roles', 'nom': 'Gérer les rôles', 'categorie': 'admin'},
        
        # Rapports
        {'code': 'rapports.voir', 'nom': 'Voir les rapports', 'categorie': 'rapports'},
        {'code': 'rapports.exporter', 'nom': 'Exporter les rapports', 'categorie': 'rapports'},
        
        # Paramètres
        {'code': 'admin.parametres', 'nom': 'Gérer les paramètres système', 'categorie': 'admin'},
        
        # Base de connaissances
        {'code': 'kb.creer', 'nom': 'Créer des articles KB', 'categorie': 'base_connaissance'},
        {'code': 'kb.modifier', 'nom': 'Modifier les articles KB', 'categorie': 'base_connaissance'},
        {'code': 'kb.voir', 'nom': 'Voir la base de connaissances', 'categorie': 'base_connaissance'},
    ]
    
    permissions_creees = []
    for perm_data in permissions_data:
        # Vérifier si la permission existe déjà
        perm = Permission.query.filter_by(code=perm_data['code']).first()
        if not perm:
            perm = Permission(
                code=perm_data['code'],
                nom=perm_data['nom'],
                categorie=perm_data['categorie'],
                description=f"Permission pour {perm_data['nom'].lower()}"
            )
            db.session.add(perm)
            permissions_creees.append(perm)
    
    db.session.commit()
    print(f"✓ {len(permissions_creees)} permissions créées")
    
    return Permission.query.all()


def initialiser_roles(permissions):
    """Créer les rôles par défaut"""
    # Créer un dictionnaire des permissions par code
    perms_dict = {p.code: p for p in permissions}
    
    roles_data = [
        {
            'nom': 'Super Administrateur',
            'description': 'Accès complet à toutes les fonctionnalités',
            'couleur': '#DC2626',
            'niveau': 100,
            'systeme': True,
            'permissions': list(perms_dict.values())  # Toutes les permissions
        },
        {
            'nom': 'Administrateur',
            'description': 'Gestion des utilisateurs, départements et tickets',
            'couleur': '#EA580C',
            'niveau': 90,
            'systeme': True,
            'permissions': [
                perms_dict['tickets.creer'],
                perms_dict['tickets.voir_tous'],
                perms_dict['tickets.modifier'],
                perms_dict['tickets.supprimer'],
                perms_dict['tickets.assigner'],
                perms_dict['tickets.fermer'],
                perms_dict['admin.utilisateurs'],
                perms_dict['utilisateurs.voir'],
                perms_dict['admin.departements'],
                perms_dict['departements.voir'],
                perms_dict['admin.categories'],
                perms_dict['rapports.voir'],
                perms_dict['rapports.exporter'],
                perms_dict['kb.creer'],
                perms_dict['kb.modifier'],
                perms_dict['kb.voir'],
            ]
        },
        {
            'nom': 'Manager',
            'description': 'Gestion des tickets de son département',
            'couleur': '#2563EB',
            'niveau': 70,
            'systeme': True,
            'permissions': [
                perms_dict['tickets.creer'],
                perms_dict['tickets.voir_tous'],
                perms_dict['tickets.modifier'],
                perms_dict['tickets.assigner'],
                perms_dict['tickets.fermer'],
                perms_dict['utilisateurs.voir'],
                perms_dict['departements.voir'],
                perms_dict['rapports.voir'],
                perms_dict['kb.creer'],
                perms_dict['kb.modifier'],
                perms_dict['kb.voir'],
            ]
        },
        {
            'nom': 'Agent',
            'description': 'Traitement des tickets assignés',
            'couleur': '#10B981',
            'niveau': 50,
            'systeme': True,
            'permissions': [
                perms_dict['tickets.creer'],
                perms_dict['tickets.modifier'],
                perms_dict['tickets.fermer'],
                perms_dict['departements.voir'],
                perms_dict['kb.voir'],
            ]
        },
        {
            'nom': 'Utilisateur',
            'description': 'Création et suivi de ses propres tickets',
            'couleur': '#6B7280',
            'niveau': 10,
            'systeme': True,
            'permissions': [
                perms_dict['tickets.creer'],
                perms_dict['kb.voir'],
            ]
        },
    ]
    
    roles_crees = []
    for role_data in roles_data:
        # Vérifier si le rôle existe déjà
        role = Role.query.filter_by(nom=role_data['nom']).first()
        if not role:
            permissions_role = role_data.pop('permissions')
            role = Role(**role_data)
            role.permissions.extend(permissions_role)
            db.session.add(role)
            roles_crees.append(role)
    
    db.session.commit()
    print(f"✓ {len(roles_crees)} rôles créés")
    
    return Role.query.all()


def creer_admin():
    """Créer un utilisateur administrateur par défaut"""
    admin = Utilisateur.query.filter_by(email='admin@example.com').first()
    
    if not admin:
        role_admin = Role.query.filter_by(nom='Super Administrateur').first()
        
        admin = Utilisateur(
            nom='Administrateur',
            prenom='Cosmitto',
            email='admin@example.com',
            matricule='ADMIN001',
            role_id=role_admin.id if role_admin else None,
            actif=True
        )
        admin.set_password('testtest')  # Mot de passe par défaut
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"✓ Utilisateur administrateur créé:")
        print(f"  Email: admin@example.com")
        print(f"  Mot de passe: testtest")
        print(f"  ⚠️  IMPORTANT: Changez ce mot de passe immédiatement!")
    else:
        print("✓ Utilisateur administrateur existe déjà")
    
    return admin


def creer_departements_exemples():
    """Créer quelques départements d'exemple"""
    departements_data = [
        {
            'nom': 'Support IT',
            'code': 'IT',
            'description': 'Support informatique et technique',
            'couleur': '#3B82F6',
            'icone': 'laptop',
        },
        {
            'nom': 'Ressources Humaines',
            'code': 'RH',
            'description': 'Gestion des ressources humaines',
            'couleur': '#10B981',
            'icone': 'users',
        },
        {
            'nom': 'Finances',
            'code': 'FIN',
            'description': 'Département financier et comptabilité',
            'couleur': '#F59E0B',
            'icone': 'dollar-sign',
        },
        {
            'nom': 'Achats',
            'code': 'ACH',
            'description': 'Gestion des achats et approvisionnements',
            'couleur': '#8B5CF6',
            'icone': 'shopping-cart',
        },
    ]
    
    departements_crees = []
    for dept_data in departements_data:
        dept = Departement.query.filter_by(code=dept_data['code']).first()
        if not dept:
            dept = Departement(**dept_data)
            db.session.add(dept)
            departements_crees.append(dept)
    
    db.session.commit()
    print(f"✓ {len(departements_crees)} départements d'exemple créés")


def initialiser_base_donnees():
    """Fonction principale d'initialisation"""
    print("\n" + "="*60)
    print("  INITIALISATION DE LA BASE DE DONNÉES COSMITTODESK 2.0")
    print("="*60 + "\n")
    
    # Créer toutes les tables
    print("Création des tables...")
    db.create_all()
    print("✓ Tables créées\n")
    
    # Initialiser les permissions
    print("Initialisation des permissions...")
    permissions = initialiser_permissions()
    print()
    
    # Initialiser les rôles
    print("Initialisation des rôles...")
    roles = initialiser_roles(permissions)
    print()
    
    # Créer l'admin
    print("Création de l'utilisateur administrateur...")
    admin = creer_admin()
    print()
    
    # Créer des départements d'exemple
    print("Création de départements d'exemple...")
    creer_departements_exemples()
    print()
    
    print("="*60)
    print("  INITIALISATION TERMINÉE AVEC SUCCÈS!")
    print("="*60)
    print("\nVous pouvez maintenant vous connecter avec:")
    print("  Email: admin@example.com")
    print("  Mot de passe: testtest")
    print("\n⚠️  N'oubliez pas de changer le mot de passe administrateur!")
    print()


if __name__ == '__main__':
    from app import create_app
    app = create_app()
    
    with app.app_context():
        initialiser_base_donnees()
