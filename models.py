from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

from utils.crypto import EncryptedString

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())


# Table d'association pour les rôles et permissions
roles_permissions = db.Table('roles_permissions',
    db.Column('role_id', db.String(36), db.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True, index=True),
    db.Column('permission_id', db.String(36), db.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True, index=True)
)

# Tables d'association pour la collaboration sur les tickets
ticket_collaborateurs = db.Table('ticket_collaborateurs',
    db.Column('ticket_id', db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), primary_key=True, index=True),
    db.Column('utilisateur_id', db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), primary_key=True, index=True)
)

ticket_departements_collab = db.Table('ticket_departements_collab',
    db.Column('ticket_id', db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), primary_key=True, index=True),
    db.Column('departement_id', db.String(36), db.ForeignKey('departements.id', ondelete='CASCADE'), primary_key=True, index=True)
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
        # Le super administrateur (niveau 100) a toutes les permissions implicitement
        if self.niveau >= 100:
            return True
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
    
    # Remote Access
    anydesk_id = db.Column(db.String(50))
    anydesk_password = db.Column(EncryptedString)      # chiffré au repos
    teamviewer_id = db.Column(db.String(50))
    teamviewer_password = db.Column(EncryptedString)   # chiffré au repos
    poste_machine = db.Column(db.String(100))
    
    # Rôle & Attachements
    role_id = db.Column(db.String(36), db.ForeignKey('roles.id', ondelete='SET NULL'), index=True)
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id', ondelete='SET NULL'), index=True)
    pdv_id = db.Column(db.String(36), db.ForeignKey('points_de_vente.id', ondelete='SET NULL'), index=True)
    entreprise_id = db.Column(db.String(36), db.ForeignKey('entreprises.id', ondelete='SET NULL'), index=True)
    
    # Paramètres
    langue = db.Column(db.String(10), default='fr')
    theme = db.Column(db.String(20), default='light')  # light, dark, auto
    couleur = db.Column(db.String(20), default='#E8213F')
    notifications_email = db.Column(db.Boolean, default=True)
    notifications_push = db.Column(db.Boolean, default=True)
    
    # État
    actif = db.Column(db.Boolean, default=True)
    verrouille = db.Column(db.Boolean, default=False)
    date_verrouillage = db.Column(db.DateTime)  # début du verrouillage temporaire
    session_version = db.Column(db.Integer, nullable=False, default=0, server_default='0')  # invalide les sessions
    tentatives_connexion = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime)
    derniere_activite = db.Column(db.DateTime)

    # Relations
    role = db.relationship('Role', backref='utilisateurs')
    departement = db.relationship('Departement', foreign_keys=[departement_id], backref='membres')
    pdv = db.relationship('PointDeVente', foreign_keys=[pdv_id], backref='employes')
    entreprise = db.relationship('Entreprise', foreign_keys=[entreprise_id], backref=db.backref('employes', lazy='dynamic'))
    tickets_crees = db.relationship('Ticket', foreign_keys='Ticket.createur_id', backref='createur')
    tickets_assignes = db.relationship('Ticket', foreign_keys='Ticket.assigne_a_id', backref='assigne_a')
    commentaires = db.relationship('Commentaire', backref='auteur', cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='utilisateur', cascade='all, delete-orphan')

    def set_password(self, password):
        self.mot_de_passe_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.mot_de_passe_hash, password)

    def get_id(self):
        """Identifiant de session = id + version : incrémenter session_version déconnecte toutes les sessions."""
        return f"{self.id}:{self.session_version or 0}"

    def revoke_sessions(self):
        self.session_version = (self.session_version or 0) + 1

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


class PointDeVente(db.Model):
    """Modèle pour un Point de Vente physique"""
    __tablename__ = 'points_de_vente'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    adresse = db.Column(db.Text)
    telephone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    localisation = db.Column(db.String(200))
    categorie = db.Column(db.String(50), default='Urbain')  # Ex: Urbain, Express, Mall, ou personnalisé
    
    responsable_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)
    responsable = db.relationship('Utilisateur', foreign_keys=[responsable_id])
    
    actif = db.Column(db.Boolean, default=True)
    couleur = db.Column(db.String(30), default='#10b981')
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PointDeVente {self.nom}>'


class Equipement(db.Model):
    """Matériel informatique ou autre d'un Point de Vente"""
    __tablename__ = 'equipements'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    pdv_id = db.Column(db.String(36), db.ForeignKey('points_de_vente.id', ondelete='CASCADE'), nullable=False, index=True)
    
    type_equipement = db.Column(db.String(50), nullable=False) # e.g., Camera, Netbox, Routeur Wi-Fi, Imprimante, Scanner, TPE, etc.
    marque = db.Column(db.String(100))
    modele = db.Column(db.String(100))
    numero_serie = db.Column(db.String(100), unique=True)
    adresse_ip = db.Column(db.String(50))
    adresse_mac = db.Column(db.String(50))
    
    statut = db.Column(db.String(20), default='actif') # actif, en_panne, maintenance, hors_service
    date_installation = db.Column(db.DateTime)
    notes = db.Column(db.Text)

    pdv = db.relationship('PointDeVente', backref=db.backref('equipements', cascade='all, delete-orphan'))

    def __repr__(self):
        return f'<Equipement {self.type_equipement} - {self.numero_serie}>'


class Entreprise(db.Model):
    """Modèle pour une Entreprise / Société (interne ou externe/prestataire)"""
    __tablename__ = 'entreprises'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False, unique=True)
    code = db.Column(db.String(20), unique=True)
    description = db.Column(db.Text)
    type_entreprise = db.Column(db.String(50), default='externe')  # 'principale', 'filiale', 'externe', 'partenaire', 'prestataire'
    email = db.Column(db.String(120))
    telephone = db.Column(db.String(20))
    adresse = db.Column(db.Text)
    site_web = db.Column(db.String(200))
    couleur = db.Column(db.String(30), default='#6366F1')
    logo = db.Column(db.String(255))
    actif = db.Column(db.Boolean, default=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def nombre_employes(self):
        return self.employes.count()

    def __repr__(self):
        return f'<Entreprise {self.nom}>'



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
    responsable_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)
    
    # Paramètres SLA
    sla_reponse_heures = db.Column(db.Integer, default=4)  # Heures pour première réponse
    sla_resolution_heures = db.Column(db.Integer, default=48)  # Heures pour résolution
    horaires_travail = db.Column(db.JSON)  # JSON des horaires
    
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
        return Ticket.query.filter(
            Ticket.departement_id == self.id,
            Ticket.statut.notin_(['resolu', 'ferme', 'annule'])
        ).count()

    def __repr__(self):
        return f'<Departement {self.nom}>'


class CategorieTicket(db.Model):
    __tablename__ = 'categories_tickets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    type_ticket = db.Column(db.String(20), default='demande')  # demande, besoin, plainte, incident, tache
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id', ondelete='CASCADE'), nullable=False, index=True)
    priorite_defaut = db.Column(db.String(20), default='moyenne')  # basse, moyenne, haute, urgente, critique
    delai_resolution_jours = db.Column(db.Integer, default=7)
    
    # Workflow
    etapes_workflow = db.Column(db.JSON)  # JSON des étapes personnalisées
    auto_assignation = db.Column(db.Boolean, default=False)
    
    # Paramètres
    couleur = db.Column(db.String(20), default='#3B82F6')
    icone = db.Column(db.String(50), default='ticket')
    formulaire_personnalise = db.Column(db.JSON)  # JSON du formulaire
    
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
    createur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='RESTRICT'), nullable=False, index=True)
    assigne_a_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)

    # Catégorie & Routage direct
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id', ondelete='SET NULL'), index=True)
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id', ondelete='SET NULL'), index=True)
    pdv_id = db.Column(db.String(36), db.ForeignKey('points_de_vente.id', ondelete='SET NULL'), index=True)

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
    donnees_personnalisees = db.Column(db.JSON)  # JSON
    tags = db.Column(db.JSON)  # JSON array de tags

    # Relations
    commentaires = db.relationship('Commentaire', backref='ticket', cascade='all, delete-orphan', 
                                   order_by='Commentaire.date_creation')
    pieces_jointes = db.relationship('PieceJointe', backref='ticket', cascade='all, delete-orphan')
    historique = db.relationship('HistoriqueTicket', backref='ticket', cascade='all, delete-orphan', 
                                order_by='HistoriqueTicket.date_creation.desc()')
    taches = db.relationship('Tache', backref='ticket', cascade='all, delete-orphan')
    departement_associe = db.relationship('Departement', foreign_keys=[departement_id])
    pdv_associe = db.relationship('PointDeVente', foreign_keys=[pdv_id], backref='tickets_associes')

    # Collaborations
    collaborateurs = db.relationship('Utilisateur', secondary=ticket_collaborateurs, lazy='subquery',
                                     backref=db.backref('tickets_en_collaboration', lazy=True))
    departements_collab = db.relationship('Departement', secondary=ticket_departements_collab, lazy='subquery',
                                          backref=db.backref('tickets_en_collaboration', lazy=True))

    @property
    def departement(self):
        if self.departement_associe:
            return self.departement_associe
        if self.categorie:
            return self.categorie.departement
        return None

    @staticmethod
    def generer_numero():
        """Génère un numéro de ticket séquentiel (séquence PostgreSQL atomique, repli sur comptage)"""
        if db.engine.dialect.name == 'postgresql':
            try:
                return str(db.session.execute(db.text("SELECT nextval('ticket_numero_seq')")).scalar())
            except Exception:
                db.session.rollback()
        count = db.session.query(db.func.count(Ticket.id)).scalar()
        next_num = count + 1
        while Ticket.query.filter_by(numero=str(next_num)).first() is not None:
            next_num += 1
        return str(next_num)

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
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    assigne_a_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)
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
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    auteur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, index=True)
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
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    commentaire_id = db.Column(db.String(36), db.ForeignKey('commentaires.id', ondelete='CASCADE'), nullable=True, index=True)
    nom_fichier = db.Column(db.String(255), nullable=False)
    nom_original = db.Column(db.String(255), nullable=False)
    type_mime = db.Column(db.String(100))
    taille = db.Column(db.Integer)
    chemin = db.Column(db.String(500), nullable=False)
    miniature = db.Column(db.String(500))  # Pour les images
    date_upload = db.Column(db.DateTime, default=datetime.utcnow)
    uploade_par_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)

    uploade_par = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<PieceJointe {self.nom_original}>'


class HistoriqueTicket(db.Model):
    __tablename__ = 'historique_tickets'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    ticket_id = db.Column(db.String(36), db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    utilisateur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)
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
    utilisateur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, index=True)
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
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id', ondelete='CASCADE'), index=True)
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id', ondelete='CASCADE'), index=True)
    meta_data = db.Column(db.JSON)  # JSON pour données supplémentaires

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
    categorie_id = db.Column(db.String(36), db.ForeignKey('categories_tickets.id', ondelete='CASCADE'), index=True)
    departement_id = db.Column(db.String(36), db.ForeignKey('departements.id', ondelete='CASCADE'), index=True)
    public = db.Column(db.Boolean, default=False)
    createur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), index=True)
    utilisation_count = db.Column(db.Integer, default=0)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    categorie = db.relationship('CategorieTicket')
    departement = db.relationship('Departement')
    createur = db.relationship('Utilisateur')

    def __repr__(self):
        return f'<ModeleReponse {self.titre}>'


class Message(db.Model):
    """Messages du chat interne"""
    __tablename__ = 'messages'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    sender_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, index=True)
    receiver_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False)
    
    # Relations
    sender = db.relationship('Utilisateur', foreign_keys=[sender_id], backref=db.backref('messages_sent', lazy='dynamic'))
    receiver = db.relationship('Utilisateur', foreign_keys=[receiver_id], backref=db.backref('messages_received', lazy='dynamic'))

    def __repr__(self):
        return f'<Message {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content,
            'timestamp': self.timestamp.isoformat() + 'Z',
            'is_read': self.is_read
        }

class PlanActionTask(db.Model):
    """Tâches pour le plan d'action (Projets IT, Interventions, etc)"""
    __tablename__ = 'plan_action_tasks'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    statut = db.Column(db.String(50), default='planned') # planned, progress, completed
    urgent = db.Column(db.Boolean, default=False)
    
    date_debut = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    date_fin = db.Column(db.DateTime, nullable=True)
    
    createur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    assigne_a_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='SET NULL'), nullable=True)

    createur = db.relationship('Utilisateur', foreign_keys=[createur_id])
    assigne_a = db.relationship('Utilisateur', foreign_keys=[assigne_a_id])

    def __repr__(self):
        return f'<PlanActionTask {self.titre}>'

class Suggestion(db.Model):
    """Suggestions et retours des utilisateurs sur la plateforme"""
    __tablename__ = 'suggestions'

    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    type_suggestion = db.Column(db.String(50), default='amelioration') # bug, amelioration, nouvelle_fonctionnalite
    statut = db.Column(db.String(50), default='nouveau') # nouveau, lu, accepte, refuse, en_cours, termine
    
    auteur_id = db.Column(db.String(36), db.ForeignKey('utilisateurs.id', ondelete='CASCADE'), nullable=False)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)

    auteur = db.relationship('Utilisateur', foreign_keys=[auteur_id])

    def __repr__(self):
        return f'<Suggestion {self.titre}>'

class CategorieConnaissance(db.Model):
    __tablename__ = 'categories_connaissance'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nom = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    icone = db.Column(db.String(50), default='folder', nullable=True)
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    articles = db.relationship(
        'ArticleConnaissance',
        back_populates='categorie',
        cascade='all, delete-orphan',
        lazy=True
    )

class ArticleConnaissance(db.Model):
    __tablename__ = 'articles_connaissance'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    titre = db.Column(db.String(255), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    categorie_id = db.Column(
        db.String(36),
        db.ForeignKey('categories_connaissance.id', ondelete='CASCADE'),
        nullable=False
    )
    auteur_id = db.Column(
        db.String(36),
        db.ForeignKey('utilisateurs.id', ondelete='CASCADE'),
        nullable=False
    )
    date_creation = db.Column(db.DateTime, default=datetime.utcnow)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    vues = db.Column(db.Integer, default=0)
    statut = db.Column(db.String(20), default='publie')
    categorie = db.relationship('CategorieConnaissance', back_populates='articles')
    auteur = db.relationship('Utilisateur', foreign_keys=[auteur_id])


class ConfigurationSysteme(db.Model):
    """Paramètres système et préférences clés-valeurs (ex: ordre des catégories de permissions)"""
    __tablename__ = 'configurations_systeme'

    cle = db.Column(db.String(100), primary_key=True)
    valeur = db.Column(db.Text, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    date_mise_a_jour = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @classmethod
    def get_valeur(cls, cle, defaut=None):
        cfg = cls.query.filter_by(cle=cle).first()
        return cfg.valeur if cfg else defaut

    @classmethod
    def set_valeur(cls, cle, valeur, description=None):
        cfg = cls.query.filter_by(cle=cle).first()
        if not cfg:
            cfg = cls(cle=cle, valeur=str(valeur), description=description)
            db.session.add(cfg)
        else:
            cfg.valeur = str(valeur)
            if description:
                cfg.description = description
        db.session.commit()
        return cfg
