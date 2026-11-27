# Tests d'intégration CosmiCenter

Scripts autonomes (pas de framework) qui testent l'application **réelle** avec `app.test_client()` sur la base définie dans `.env`.
Ils retrouvent seuls la racine du projet : on peut les lancer **depuis n'importe quel dossier**, et le projet peut être déplacé (autre PC, disque externe…).

```
venv\Scripts\python.exe tests\cat_test.py        (Windows)
venv/bin/python tests/cat_test.py                (Linux / macOS)
```

| Script | Vérifie |
|---|---|
| `nav_test.py` | navigation, badges, permissions, rapports, messagerie |
| `chat_test.py` | messagerie et pièces jointes |
| `groups_test.py` | groupes de discussion (création, droits, membres, fichiers, suppression) |
| `kb_views_test.py` | base de connaissances : lecteurs distincts et nombre de lectures par personne |
| `pdv_ref_test.py` | catégories et thèmes des points de vente (base + cache) |
| `ticket_pdv_test.py` | ticket adressé à un point de vente : choix, notifications, visibilité |
| `plan_action_test.py` | plan d'action personnel : chacun ne voit / modifie / exporte que ses tâches |
| `sound_pref_test.py` | préférence « Sons des notifications » du profil + thème absent du profil |
| `pdv_scope_test.py` | sans `pdv.tous`, on ne modifie / gère que ses propres PDV (serveur + boutons) |
| `cat_test.py` | gestion des catégories de tickets (créer, modifier, archiver, supprimer, permission) |
| `report_test.py` | rapport global, filtres, export CSV |
| `agents_test.py` | performance des agents et fiche agent |
| `super_admin_test.py` | un compte avec toutes les permissions (sans être Super Administrateur) ne peut rien faire sur un Super Administrateur ni sur son rôle |
| `portability_test.py` | **aucun chemin absolu** (C:\, /Users/, /home/nom/…) dans le code, les gabarits, les scripts, les docs, le `.env` ni les données de la base ; fichiers référencés présents dans le dossier du projet |
| `ticket_scope_test.py` | portée des actions tickets : `tickets.<action>` (tous) vs `tickets.<action>_mes` (mes tickets), sans base |
| `ticket_scope_http_test.py` | page Rôles (cases rangées sous « Mes tickets » / « Tous les tickets ») et commentaires réellement limités à la portée du droit ; rôles/utilisateurs/tickets de test supprimés |
| `permissions_enforcement_test.py` | **chaque permission est appliquée par le serveur** : plus de niveaux, menu seul → page protégée, tickets (modifier / clôturer / supprimer), suppression utilisateur et PDV, protection du Super Administrateur, garde-fou du rôle racine ; tout est nettoyé |
| `prod_test.py`, `proxy_test.py` | configuration de production et ProxyFix |
| `dbq.py` | requêtes SQL **en lecture seule** : `python tests\dbq.py "select count(*) from tickets"` |
| `seed_sample_tickets.py` | `seed` / `clean` : 140 tickets d'exemple pour regarder les rapports |

**Principe :** chaque test crée des utilisateurs/données temporaires (`zz.*@example.invalid`, `ZZ…`), vérifie, puis supprime tout (`finally`).
Base de référence attendue après les tests : **3 tickets, 69 utilisateurs, 8 points de vente**. Certains tests supposent des données existantes (département « Stock », rôle « Super Administrateur », 42 catégories).
**Ne lancez pas ces scripts sur une base de production.**

- `permissions_test.py` : toute permission du code existe dans « Rôles » ; un rôle de test ne peut faire que ce qui est coché (Boîte à idées…).
