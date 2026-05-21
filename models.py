from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
import json

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())


# Table d'association pour les rôles et permissions
roles_permissions = db.Table('roles_permissions',
    db.Column('role_id', db.String(36), db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.String(36), db.ForeignKey('permissions.id'), primary_key=True)
)


class Permission(db.Model):
    """Permissions granulaires pour le système"""
    __tablename__ = 'permissions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    code = db.Column(db.String(100), unique=True, nullable=False)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    categorie = db.Column(db.String(50))  # tickets, utilisateurs, departements, etc.
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Permission {self.code}>'


class Role(db.Model):
    """Rôles personnalisables avec permissions"""
    __tablename__ = 'roles'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    couleur = db.Column(db.String(20), default='#3B82F6')  # Couleur pour l'UI
    niveau = db.Column(db.Integer, default=0)  # Hiérarchie des rôles
    systeme = db.Column(db.Boolean, default=False)  # Rôle système non modifiable
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    permissions = db.relationship('Permission', secondary=roles_permissions, 
                                 backref=db.backref('roles', lazy='dynamic'))

    def has_permission(self, permission_code):
        """Vérifie si le rôle a une permission spécifique"""
        return any(p.code == permission_code for p in self.permissions)

    def __repr__(self):
        return f'<Role {self.nom}>'


class Utilisateur(UserMixin, db.Model):
    __tablename__ = 'utilisateurs'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    mot_de_passe_hash = db.Column(db.String(255), nullable=False)
    telephone = db.Column(db.String(20))
    poste = db.Column(db.String(100))  # Titre du poste
    matricule = db.Column(db.String(50), unique=True)
    photo_profil = db.Column(db.String(255))
    
    # Rôle
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id'))
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id'))
    
    # Paramètres
    langue = db.Column(db.String(10), default='fr')
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    notifications_email = db.Column(db.Boolean, default=True)
    notifications_push = db.Column(db.Boolean, default=True)
    
    # État
    actif = db.Column(db.Boolean, default=True)
    verrouille = db.Column(db.Boolean, default=False)
    tentatives_connexion = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime)
    derniere_activite = db.Column(db.DateTime)

    # Relations
    role = db.relationship('Role', backref='utilisateurs')
    departement = db.relationship('Departement', foreign_keys=[departement_id], backref='membres')
    tickets_crees = db.relationship('Ticket', foreign_keys='Ticket.createur_id', backref='createur')
    tickets_assignes = db.relationship('Ticket', foreign_keys='Ticket.assigne_a_id', backref='assigne_a')
    commentaires = db.relationship('Commentaire', backref='auteur', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='utilisateur', cascade='all, delete-orphan')

    def set_password(self, password):
        self.mot_de_passe_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe_hash, password)

    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

    def has_permission(self, permission_code):
        """Vérifie si l'utilisateur a une permission spécifique"""
        if not self.role:
            return False
        return self.role.has_permission(permission_code)

    def __repr__(self):
        return f'<Utilisateur {self.email}>'


class Departement(db.Model):
    __tablename__ = 'departements'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    localisation = db.Column(db.String(200))
    couleur = db.Column(db.String(20), default='#3B82F6')
    icone = db.Column(db.String(50), default='building')
    
    # Responsable
    responsable_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))
    
    # Paramètres SLA
    sla_reponse_heures = db.Column(db.Integer, default=4)  # Heures pour première réponse
    sla_resolution_heures = db.Column(db.Integer, default=48)  # Heures pour résolution
    horaires_travail = db.Column(db.Text)  # JSON des horaires
    
    # État
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    responsable = db.relationship('Utilisateur', foreign_keys=[responsable_id])
    categories = db.relationship('CategorieTicket', backref='departement', cascade='all, delete-orphan')

    @property
    def nombre_membres(self):
        return len(self.membres)

    @property
    def tickets_actifs(self):
        return sum(1 for cat in self.categories for ticket in cat.tickets 
                  if ticket.statut not in ['resolu', 'ferme'])

    def __repr__(self):
        return f'<Departement {self.nom}>'


class CategorieTicket(db.Model):
    __tablename__ = 'categories_tickets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type_ticket = db.Column(db.String(20), default='demande')  # demande, besoin, plainte, incident, tache
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id'), nullable=False)
    priorite_defaut = db.Column(db.String(20), default='moyenne')  # basse, moyenne, haute, urgente, critique
    delai_resolution_jours = db.Column(db.Integer, default=7)
    
    # Workflow
    etapes_workflow = db.Column(db.Text)  # JSON des étapes personnalisées
    auto_assignation = db.Column(db.Boolean, default=False)
    
    # Paramètres
    couleur = db.Column(db.String(20), default='#3B82F6')
    icone = db.Column(db.String(50), default='ticket')
    formulaire_personnalise = db.Column(db.Text)  # JSON du formulaire
    
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    # Relations
    tickets = db.relationship('Ticket', backref='categorie')

    def __repr__(self):
        return f'<CategorieTicket {self.nom}>'


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    numero = db.Column(db.String(20), unique=True, nullable=False, index=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type_ticket = db.Column(db.String(20), nullable=False)
    priorite = db.Column(db.String(20), default='moyenne')
    statut = db.Column(db.String(20), default='nouveau')  # nouveau, en_cours, en_attente, resolu, ferme, annule
    
    # Impact et urgence (pour calcul automatique priorité)
    impact = db.Column(db.String(20))  # faible, moyen, eleve, critique
    urgence = db.Column(db.String(20))  # faible, moyenne, elevee, critique

    # Relations utilisateurs
    createur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'), nullable=False)
    assigne_a_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))

    # Catégorie
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id'))

    # Dates
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    date_echeance = db.Column(db.DateTime)
    date_premiere_reponse = db.Column(db.DateTime)
    date_resolution = db.Column(db.DateTime)
    date_fermeture = db.Column(db.DateTime)

    # SLA
    sla_respecte = db.Column(db.Boolean)
    temps_premiere_reponse_minutes = db.Column(db.Integer)
    temps_resolution_minutes = db.Column(db.Integer)

    # Évaluation
    satisfaction = db.Column(db.Integer)  # Note de 1 à 5
    commentaire_satisfaction = db.Column(db.Text)

    # Champs spécifiques selon le type
    article_demande = db.Column(db.String(200))
    quantite_demandee = db.Column(db.Integer)
    unite = db.Column(db.String(50))
    nature_besoin = db.Column(db.String(200))
    justification = db.Column(db.Text)
    personne_concernee = db.Column(db.String(200))
    date_incident = db.Column(db.DateTime)
    lieu_incident = db.Column(db.String(200))
    
    # Données personnalisées
    donnees_personnalisees = db.Column(db.Text)  # JSON

    # Tags
    tags = db.Column(db.Text)  # JSON array de tags

    # Relations
    commentaires = db.relationship('Commentaire', backref='ticket', cascade='all, delete-orphan', 
                                   order_by='Commentaire.date_creation')
    pieces_jointes = db.relationship('PieceJointe', backref='ticket', cascade='all, delete-orphan')
    historique = db.relationship('HistoriqueTicket', backref='ticket', cascade='all, delete-orphan', 
                                order_by='HistoriqueTicket.date_creation.desc()')
    taches = db.relationship('Tache', backref='ticket', cascade='all, delete-orphan')

    @staticmethod
    def generer_numero():
        """Génère un numéro de ticket unique"""
        timestamp = datetime.now().strftime('%Y%m%d')
        import random
        random_num = random.randint(1000, 9999)
        return f"TKT-{timestamp}-{random_num}"

    def calculer_priorite_automatique(self):
        """Calcule la priorité basée sur impact et urgence"""
        matrice = {
            ('critique', 'critique'): 'critique',
            ('critique', 'elevee'): 'critique',
            ('eleve', 'critique'): 'critique',
            ('eleve', 'elevee'): 'urgente',
            ('moyen', 'elevee'): 'urgente',
            ('eleve', 'moyenne'): 'haute',
            ('moyen', 'moyenne'): 'moyenne',
            ('faible', 'moyenne'): 'basse',
            ('faible', 'faible'): 'basse',
        }
        return matrice.get((self.impact, self.urgence), 'moyenne')

    def __repr__(self):
        return f'<Ticket {self.numero}>'


class Tache(db.Model):
    """Sous-tâches dans un ticket"""
    __tablename__ = 'taches'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigne_a_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))
    terminee = db.Column(db.Boolean, default=False)
    ordre = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_echeance = db.Column(db.DateTime)
    date_completion = db.Column(db.DateTime)

    assigne_a = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<Tache {self.titre}>'


class Commentaire(db.Model):
    __tablename__ = 'commentaires'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id'), nullable=False)
    auteur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    interne = db.Column(db.Boolean, default=False)
    type_commentaire = db.Column(db.String(20), default='commentaire')  # commentaire, solution, note
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    modifie = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<Commentaire {self.id}>'


class PieceJointe(db.Model):
    __tablename__ = 'pieces_jointes'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id'), nullable=False)
    nom_fichier = db.Column(db.String(255), nullable=False)
    nom_original = db.Column(db.String(255), nullable=False)
    type_mime = db.Column(db.String(100))
    taille = db.Column(db.Integer)
    chemin = db.Column(db.String(500), nullable=False)
    miniature = db.Column(db.String(500))  # Pour les images
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    uploade_par_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))

    uploade_par = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<PieceJointe {self.nom_original}>'


class HistoriqueTicket(db.Model):
    __tablename__ = 'historique_tickets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id'), nullable=False)
    utilisateur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    champ_modifie = db.Column(db.String(100))
    ancienne_valeur = db.Column(db.Text)
    nouvelle_valeur = db.Column(db.Text)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    utilisateur = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<HistoriqueTicket {self.action}>'


class Notification(db.Model):
    """Notifications pour les utilisateurs"""
    __tablename__ = 'notifications'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    utilisateur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'), nullable=False)
    titre = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text)
    type_notification = db.Column(db.String(50))  # ticket, mention, systeme, etc.
    lien = db.Column(db.String(500))
    lue = db.Column(db.Boolean, default=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_lecture = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Notification {self.titre}>'


class Statistique(db.Model):
    __tablename__ = 'statistiques'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    date = db.Column(db.Date, nullable=False)
    type_stat = db.Column(db.String(50), nullable=False)
    valeur = db.Column(db.Integer, default=0)
    valeur_float = db.Column(db.Float)  # Pour les moyennes, pourcentages
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id'))
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id'))
    meta_data = db.Column(db.Text)  # JSON pour données supplémentaires

    departement = db.relationship('Departement')
    categorie = db.relationship('CategorieTicket')

    def __repr__(self):
        return f'<Statistique {self.type_stat} - {self.date}>'


class ModeleReponse(db.Model):
    """Modèles de réponses prédéfinies"""
    __tablename__ = 'modeles_reponses'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id'))
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id'))
    public = db.Column(db.Boolean, default=False)
    createur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))
    utilisation_count = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    categorie = db.relationship('CategorieTicket')
    departement = db.relationship('Departement')
    createur = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<ModeleReponse {self.titre}>'


class BaseConnaissance(db.Model):
    """Base de connaissances / FAQ"""
    __tablename__ = 'base_connaissance'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id'))
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id'))
    tags = db.Column(db.Text)  # JSON
    publique = db.Column(db.Boolean, default=True)
    auteur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id'))
    vues = db.Column(db.Integer, default=0)
    utile_count = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_modification = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categorie = db.relationship('CategorieTicket')
    departement = db.relationship('Departement')
    auteur = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<BaseConnaissance {self.titre}>'
