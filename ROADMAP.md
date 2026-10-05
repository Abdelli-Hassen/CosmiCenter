# ROADMAP & TODO — CosmittoHUB

Ce document liste les fonctionnalités restantes pour finaliser la version 1.0, ainsi que les pistes d'amélioration pour faire évoluer l'application vers un standard d'entreprise complet (type Jira/Zendesk).

---

## 🚧 1. Les Indispensables (Pour finaliser la V1)
*Ces éléments sont déjà prévus dans l'architecture mais nécessitent d'être codés.*


- [ ] **Paramètres et Logs Système**
  - Rendre fonctionnelles les pages d'administration "Paramètres" et "Logs système" qui sont actuellement des espaces réservés.

- [ ] **Gestion complète des Pièces Jointes**
  - S'assurer que le glisser-déposer de captures d'écran et de fichiers fonctionne de manière fluide dans les commentaires et la création de tickets.

---

## 🚀 2. Fonctionnalités "Next-Level" (Pour la V2 et au-delà)
*Ces éléments transformeront CosmittoHUB en une véritable plateforme d'entreprise.*

- [ ] **Intégration Email (Email-to-Ticket)**
  - Création automatique de tickets lorsqu'un utilisateur envoie un email à `support@example.com`.
  - Permettre aux utilisateurs de répondre aux notifications par email pour ajouter un commentaire au ticket.

- [ ] **Moteur d'Automatisations (Triggers)**
  - Règles basées sur le temps (ex: *Si un ticket est 'En attente' depuis 5 jours, relancer l'utilisateur*).
  - Règles d'assignation automatique (ex: *Assigner automatiquement les tickets 'Urgent' de la catégorie IT à l'agent d'astreinte*).

- [ ] **Réponses Pré-enregistrées (Macros)**
  - Permettre aux agents de sauvegarder des modèles de réponses pour les problèmes fréquents (ex: "Procédure de réinitialisation de mot de passe").
  - Insertion en 1 clic pour gagner du temps.

- [ ] **SLA Avancés et Escalades**
  - Notification automatique au Manager si un ticket approche de son délai de résolution (SLA).
  - Mise en surbrillance rouge dans la liste des tickets pour les SLA expirés.

- [ ] **Intégration d'outils tiers (Webhooks)**
  - Envoyer des alertes dans Microsoft Teams ou Slack lors de la création d'un ticket "Critique". 

---
*Dernière mise à jour : Octobre 2026*
