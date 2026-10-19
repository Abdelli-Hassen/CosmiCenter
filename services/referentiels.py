"""
Référentiels des points de vente (catégories, palette de thèmes), stockés dans la table existante
`configurations_systeme` (clés `pdv_categories` et `pdv_themes`, valeur JSON) et mis en cache.

- La catégorie et la couleur PROPRES à chaque PDV restent dans `points_de_vente` (colonnes categorie, couleur).
- Les listes de choix (palette, description et icône des catégories) viennent de la base : aucune liste en dur dans les pages.
- Cache mémoire (TTL) vidé à chaque modification via invalidate().
"""
import json
import threading
import time

from models import db, ConfigurationSysteme, PointDeVente

KEY_CATEGORIES = 'pdv_categories'
KEY_THEMES = 'pdv_themes'
CACHE_TTL_SECONDS = 300
_cache = {}
_lock = threading.Lock()

# Valeurs d'amorçage, insérées UNE seule fois si la clé n'existe pas encore ; ensuite tout vient de la base.
SEED_CATEGORIES = [
    {'nom': 'Urbain', 'description': 'Centre-ville & quartiers', 'icone': 'building'},
    {'nom': 'Express', 'description': 'Station-service, kiosque', 'icone': 'bolt'},
    {'nom': 'Mall', 'description': 'Centre commercial', 'icone': 'bag'},
]
SEED_THEMES = [
    ('Émeraude', '#10b981'), ('Azur', '#0ea5e9'), ('Saphir', '#2563eb'), ('Indigo', '#6366f1'),
    ('Violet', '#8b5cf6'), ('Rose', '#ec4899'), ('Corail', '#f97316'), ('Ambre', '#f59e0b'),
    ('Rouge', '#ef4444'), ('Sarcelle', '#14b8a6'), ('Ardoise', '#64748b'),
]
ICON_KEYS = ['building', 'bolt', 'bag', 'store', 'coffee', 'map-pin', 'star', 'circle']


def invalidate():
    with _lock:
        _cache.clear()


def _cached(key, loader):
    now = time.monotonic()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
    value = loader()
    with _lock:
        _cache[key] = (now, value)
    return value


# ── Lecture / écriture JSON dans configurations_systeme ────────────────────────
def _read(key):
    raw = ConfigurationSysteme.get_valeur(key, '[]')
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []


def _write(key, items, description):
    """Écrit la liste sans commit : l'appelant valide la transaction (ou appelle commit())."""
    payload = json.dumps(items, ensure_ascii=False)
    cfg = ConfigurationSysteme.query.filter_by(cle=key).first()
    if cfg is None:
        db.session.add(ConfigurationSysteme(cle=key, valeur=payload, description=description))
    else:
        cfg.valeur = payload
        cfg.description = description
    invalidate()


def _norm_categories(items):
    out = []
    for i, c in enumerate(items):
        if not isinstance(c, dict) or not str(c.get('nom', '')).strip():
            continue
        out.append({
            'nom': str(c['nom']).strip()[:50],
            'description': str(c.get('description') or '')[:200],
            'icone': c.get('icone') if c.get('icone') in ICON_KEYS else 'circle',
            'ordre': int(c.get('ordre', i + 1) or 0),
            'actif': bool(c.get('actif', True)),
        })
    return sorted(out, key=lambda c: (c['ordre'], c['nom'].lower()))


def _norm_themes(items):
    out = []
    for i, t in enumerate(items):
        if not isinstance(t, dict) or not t.get('couleur'):
            continue
        out.append({'nom': str(t.get('nom') or t['couleur'])[:50], 'couleur': str(t['couleur']).lower(),
                    'ordre': int(t.get('ordre', i + 1) or 0)})
    return sorted(out, key=lambda t: (t['ordre'], t['nom'].lower()))


# ── API de lecture (mise en cache) ──────────────────────────────────────────────
def get_all_categories():
    """Toutes les catégories, actives ou non (page d'administration)."""
    return [dict(c) for c in _cached('categories_all', lambda: _norm_categories(_read(KEY_CATEGORIES)))]


def get_categories():
    """Catégories actives (formulaires, filtres)."""
    return [c for c in get_all_categories() if c['actif']]


def get_themes():
    """Couleurs de la palette."""
    return [dict(t) for t in _cached('themes', lambda: _norm_themes(_read(KEY_THEMES)))]


# ── API d'écriture (sans commit) ────────────────────────────────────────────────
def save_categories(items):
    _write(KEY_CATEGORIES, _norm_categories(items), 'Catégories de points de vente (JSON)')


def save_themes(items):
    _write(KEY_THEMES, _norm_themes(items), 'Palette de thèmes des points de vente (JSON)')


def register_category(nom):
    """Ajoute la catégorie si elle n'existe pas (catégorie « personnalisée » saisie dans le formulaire PDV)."""
    nom = (nom or '').strip()
    cats = get_all_categories()
    if not nom or any(c['nom'].lower() == nom.lower() for c in cats):
        return False
    cats.append({'nom': nom[:50], 'description': 'Catégorie personnalisée', 'icone': 'circle',
                 'ordre': max([c['ordre'] for c in cats] + [0]) + 1, 'actif': True})
    save_categories(cats)
    return True


def ensure_defaults():
    """Amorce les listes absentes et rattache les catégories déjà portées par des PDV. Idempotent."""
    changed = False
    if ConfigurationSysteme.query.filter_by(cle=KEY_CATEGORIES).first() is None:
        save_categories([dict(c, ordre=i) for i, c in enumerate(SEED_CATEGORIES, start=1)])
        changed = True
    if ConfigurationSysteme.query.filter_by(cle=KEY_THEMES).first() is None:
        save_themes([{'nom': n, 'couleur': c, 'ordre': i} for i, (n, c) in enumerate(SEED_THEMES, start=1)])
        changed = True
    if changed:
        db.session.flush()
        invalidate()
    for (cat,) in db.session.query(PointDeVente.categorie).distinct().all():
        if cat and register_category(cat):
            changed = True
    if changed:
        db.session.commit()
    invalidate()
