# ROADMAP & TODO — Cosmicenter

Ce document liste les fonctionnalités restantes pour finaliser la version 1.0, ainsi que les pistes d'évolution.

---

## ✅ Fonctionnalités Récemment Achevées
- **Paramètres et Logs Système** : Configurables (UI, DavMail) et visualisation en direct fonctionnelle.
- **Gestion des Pièces Jointes** : Glisser-déposer (Drag & Drop) complètement implémenté en front et back.
- **Notifications UI** : Gestion via des points ("dots") plutôt que des badges numériques.
- **Design du Tableau de Bord Admin et Utilisateurs** : Complètement mis à jour avec des interfaces dynamiques et réactives.

---

- **Base de Connaissance (Knowledge Base)** : Modèles de base de données implémentés avec un système de catégories (Tech, Finance, RH) et interfaces de lecture, création, et modification intégrées.
- **Réinitialisation de Mot de Passe** : Simplifié pour diriger les utilisateurs vers le support IT directement (au lieu d'un système d'email factice).
- **Valeurs Dynamiques** : La version de l'application et l'état de la base de données dans le Dashboard Admin sont désormais chargés dynamiquement depuis la configuration du serveur.

---

## 🚧 1. Les Indispensables (Pour finaliser la V1)
*Aucune fonctionnalité indispensable restante. Le système de base (V1) est terminé.*

---

## 🚀 2. Fonctionnalités "Next-Level" (Pour la V2 et au-delà)

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
