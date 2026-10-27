# Tests d'intégration CosmiCenter

Scripts autonomes (pas de framework) qui testent l'application **réelle** avec `app.test_client()` sur la base définie dans `.env`.
Ils retrouvent seuls la racine du projet : on peut les lancer **depuis n'importe quel dossier**, et le projet peut être déplacé (autre PC, disque externe…).

```
venv\Scripts\python.exe tests\cat_test.py        (Windows)
venv/bin/python tests/cat_test.py                (Linux / macOS)
```

| Script | Vérifie |
|---|---|
| `nav_test.py` | navigation, badges, permissions, évaluation, rapports, messagerie |
| `chat_test.py` | messagerie et pièces jointes |
| `kb_views_test.py` | base de connaissances : lecteurs distincts et nombre de lectures par personne |
| `pdv_ref_test.py` | catégories et thèmes des points de vente (base + cache) |
| `cat_test.py` | gestion des catégories de tickets (créer, modifier, archiver, supprimer, permission) |
| `report_test.py` | rapport global, filtres, export CSV |
| `agents_test.py` | performance des agents et fiche agent |
| `portability_test.py` | **aucun chemin absolu** (C:\, /Users/, /home/nom/…) dans le code, les gabarits, les scripts, les docs, le `.env` ni les données de la base ; fichiers référencés présents dans le dossier du projet |
| `prod_test.py`, `proxy_test.py` | configuration de production et ProxyFix |
| `dbq.py` | requêtes SQL **en lecture seule** : `python tests\dbq.py "select count(*) from tickets"` |
| `seed_sample_tickets.py` | `seed` / `clean` : 140 tickets d'exemple pour regarder les rapports |

**Principe :** chaque test crée des utilisateurs/données temporaires (`zz.*@example.invalid`, `ZZ…`), vérifie, puis supprime tout (`finally`).
Base de référence attendue après les tests : **3 tickets, 69 utilisateurs, 8 points de vente**. Certains tests supposent des données existantes (département « Stock », rôle « Super Administrateur », 42 catégories).
**Ne lancez pas ces scripts sur une base de production.**

- `permissions_test.py` : toute permission du code existe dans « Rôles » ; un rôle de test ne peut faire que ce qui est coché (Boîte à idées…).
