# 🐐 CosmittoDesk 2.0 - Système de Gestion de Tickets Professionnel

![CosmittoDesk Logo](static/images/logo-cosmitto.png)

CosmittoDesk est une application web professionnelle de gestion de tickets (helpdesk) conçue pour les entreprises modernes. Version 2.0 avec fonctionnalités avancées, design moderne et système de permissions granulaire.

## ✨ Fonctionnalités Principales

### 🎯 Gestion Complète des Tickets
- Création, suivi et résolution de tickets (demandes, besoins, plaintes, incidents)
- Système de priorités (basse, moyenne, haute, urgente, critique)
- Workflow personnalisable par catégorie
- Assignation automatique ou manuelle
- Sous-tâches et checklist
- Pièces jointes multiples
- Commentaires et notes internes
- Historique complet des modifications

### 👥 Gestion Avancée des Utilisateurs
- Système de rôles et permissions granulaires
- 5 rôles pré-configurés (Super Admin, Admin, Manager, Agent, Utilisateur)
- Permissions personnalisables
- Gestion des départements
- Profils utilisateurs complets
- Paramètres de notification personnalisés

### 🏢 Gestion des Départements
- Création et organisation de départements
- Catégories de tickets par département
- SLA (Service Level Agreement) configurable
- Horaires de travail personnalisés
- Responsables de département
- Statistiques par département

### 📊 Rapports et Statistiques
- Tableau de bord avec métriques en temps réel
- Rapports de performance des agents
- Statistiques de satisfaction client
- Analyse des temps de résolution
- Respect des SLA
- Export en CSV
- Graphiques et visualisations

### 🔔 Notifications
- Notifications en temps réel
- Alertes par email (optionnel)
- Centre de notifications
- Paramètres personnalisables

### 📚 Base de Connaissances
- Articles FAQ
- Solutions pré-enregistrées
- Modèles de réponses
- Recherche intégrée

### 🎨 Interface Utilisateur Moderne
- Design professionnel et distinctif
- Thème clair/sombre
- Responsive (mobile, tablette, desktop)
- Animations fluides
- Typographie unique (Staatliches + IBM Plex Sans)
- Couleurs inspirées de l'identité Cosmitto

## 🚀 Installation Rapide

### Prérequis
- Python 3.8 ou supérieur
- pip (gestionnaire de paquets Python)
- (Optionnel) PostgreSQL ou MySQL pour la production

### Installation

1. **Cloner le projet**
```bash
cd CosmittoDesk2
```

2. **Créer un environnement virtuel**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configurer l'environnement**
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos paramètres
# Changez au minimum la SECRET_KEY
```

5. **Initialiser la base de données**
```bash
python scripts/init_db.py
```

6. **Lancer l'application**
```bash
python app.py
```

7. **Accéder à l'application**
Ouvrez votre navigateur et allez à: http://127.0.0.1:5000

**Connexion par défaut:**
- Email: `admin@example.com`
- Mot de passe: `testtest`

⚠️ **IMPORTANT**: Changez le mot de passe administrateur dès la première connexion!

## 📁 Structure du Projet

```
CosmittoDesk2/
│
├── app.py                  # Application Flask principale
├── config.py              # Configuration
├── models.py              # Modèles de base de données
├── requirements.txt       # Dépendances Python
├── .env.example          # Variables d'environnement (exemple)
│
├── routes/               # Routes (blueprints)
│   ├── auth.py          # Authentification
│   ├── tickets.py       # Gestion des tickets
│   ├── admin.py         # Administration
│   ├── departements.py  # Gestion des départements
│   ├── utilisateurs.py  # Gestion des utilisateurs
│   ├── rapports.py      # Rapports et statistiques
│   ├── parametres.py    # Paramètres utilisateur
│   └── api.py           # API REST
│
├── templates/           # Templates HTML
│   ├── base.html       # Template de base
│   ├── admin/          # Templates admin
│   ├── tickets/        # Templates tickets
│   ├── departements/   # Templates départements
│   ├── utilisateurs/   # Templates utilisateurs
│   ├── rapports/       # Templates rapports
│   ├── parametres/     # Templates paramètres
│   ├── auth/           # Templates authentification
│   └── errors/         # Pages d'erreur
│
├── static/             # Fichiers statiques
│   ├── css/           # Styles CSS
│   ├── js/            # JavaScript
│   ├── images/        # Images et logo
│   └── uploads/       # Fichiers uploadés
│
├── scripts/           # Scripts utilitaires
│   └── init_db.py    # Initialisation de la BDD
│
├── instance/          # Base de données SQLite
└── logs/             # Fichiers de logs
```

## 🔐 Rôles et Permissions

### Super Administrateur
- Accès complet à toutes les fonctionnalités
- Gestion des rôles et permissions
- Configuration système

### Administrateur
- Gestion des utilisateurs et départements
- Gestion complète des tickets
- Accès aux rapports
- Gestion de la base de connaissances

### Manager
- Gestion des tickets de son département
- Assignation des tickets
- Rapports de son département
- Création d'articles KB

### Agent
- Traitement des tickets assignés
- Création de tickets
- Consultation de la base de connaissances

### Utilisateur
- Création de tickets
- Suivi de ses tickets
- Consultation de la base de connaissances

## 🛠️ Configuration Avancée

### Base de Données PostgreSQL

1. Créer la base de données:
```sql
CREATE DATABASE cosmittodesk;
CREATE USER cosmitto WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE cosmittodesk TO cosmitto;
```

2. Modifier `.env`:
```
DATABASE_URL=postgresql://cosmitto:testtest@localhost:5432/cosmittodesk
```

### Configuration Email

Pour activer les notifications par email, configurez dans `.env`:
```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

**Note**: Pour Gmail, utilisez un "App Password" plutôt que votre mot de passe principal.

## 🎨 Personnalisation

### Changer le Logo
Remplacez `static/images/logo-cosmitto.png` par votre logo (recommandé: 200x200px, PNG avec fond transparent).

### Couleurs
Modifiez les variables CSS dans `templates/base.html`:
```css
:root {
    --primary: #DC2626;        /* Couleur principale */
    --secondary: #0F172A;      /* Couleur secondaire */
    --accent: #F59E0B;         /* Couleur d'accentuation */
}
```

### Nom de l'Application
Changez dans `config.py`:
```python
APP_NAME = 'Votre Nom'
```

## 📊 Commandes CLI

```bash
# Initialiser la base de données
python scripts/init_db.py

# Créer un administrateur
flask create-admin

# Réinitialiser la base de données
flask reset-db

# Lancer l'application
python app.py
```

## 🔧 Dépannage

### Erreur de base de données
```bash
# Supprimer et recréer la base de données
rm instance/cosmitto.db
python scripts/init_db.py
```

### Problème de permissions
Vérifiez que l'utilisateur a un rôle assigné et que le rôle a les bonnes permissions.

### Port déjà utilisé
Changez le port dans `.env`:
```
FLASK_PORT=8080
```

## 📝 Bonnes Pratiques

1. **Sécurité**
   - Changez toujours la `SECRET_KEY` en production
   - Utilisez HTTPS en production
   - Changez le mot de passe admin par défaut
   - Limitez les permissions des utilisateurs

2. **Performance**
   - Utilisez PostgreSQL ou MySQL en production
   - Configurez un cache (Redis)
   - Activez la compression gzip
   - Optimisez les images

3. **Maintenance**
   - Sauvegardez régulièrement la base de données
   - Consultez les logs en cas de problème
   - Mettez à jour les dépendances
   - Testez avant de déployer en production

## 🆕 Nouveautés Version 2.0

- ✅ Système de rôles et permissions granulaire
- ✅ Gestion avancée des départements
- ✅ Rapports et statistiques détaillés
- ✅ Base de connaissances intégrée
- ✅ Notifications en temps réel
- ✅ Interface utilisateur modernisée
- ✅ Sous-tâches dans les tickets
- ✅ SLA configurable
- ✅ Satisfaction client
- ✅ Export de données
- ✅ API REST
- ✅ Multi-langue (préparé)
- ✅ Thème clair/sombre

## 📄 Licence

Ce projet est sous licence propriétaire Cosmitto.

## 👥 Support

Pour toute question ou assistance:
- Email: support@example.com
- Documentation: Consultez ce README

## 🙏 Remerciements

Développé avec ❤️ pour Cosmitto.

---

**Version**: 2.0.0  
**Dernière mise à jour**: Février 2026
