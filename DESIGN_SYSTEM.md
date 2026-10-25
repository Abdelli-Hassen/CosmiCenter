# Cosmicenter - Premium Design System Guidelines

This document outlines the core aesthetic principles, CSS structures, and interactive patterns used in the new "Performance des Agents" and "Agent Profile" dashboards. 

This design system is intended to serve as the blueprint for upgrading the rest of the application to a premium, modern, and highly interactive standard.

## 1. Core Aesthetic Principles
The new design language moves away from flat, static interfaces towards a highly tactile, "glassmorphic" and deeply interactive experience. It relies on:
- **Depth & Elevation**: Elements don't just sit flat; they lift off the page using soft, layered box-shadows.
- **Dynamic Micro-Interactions**: Every actionable element (cards, rows, buttons) reacts to the user's cursor with smooth scaling, translation, and color shifts.
- **Subtle Gradients & Glass Borders**: Heavy borders are replaced with subtle `rgba()` borders and gradient masking on hover.
- **Rich Typography**: High contrast between font weights (e.g., `800` or `900` for metrics and titles, `500` or `600` for subtitles) to establish a crystal-clear visual hierarchy.

## 2. Global CSS Variables Reference
Always use these variables (defined in `variables.css`) rather than hardcoding hex colors to ensure dark-mode compatibility and consistency:

```css
/* Backgrounds */
--surface-base:   /* The main body background */
--surface-1:      /* Primary card/container background */
--surface-2:      /* Secondary background (headers, avatars, muted areas) */
--surface-hover:  /* Background color when hovering over lists/buttons */

/* Borders */
--border-subtle:  /* Very light borders for structural separation */

/* Text */
--text-primary:   /* Main high-contrast text */
--text-secondary: /* Sub-text */
--text-muted:     /* Gray/Muted text for labels */

/* Brand & Accents */
--brand:          /* The primary brand color */
```

## 3. Reusable Components & Patterns

### 3.1 KPI Cards (The "Lift-Off" Effect)
Cards must feel tactile. When hovered, they should scale up slightly, lift up (translateY), cast a deeper shadow, and reveal a subtle glowing border.

**CSS Implementation:**
```css
.kpi-card {
  background: var(--surface-1); 
  border-radius: 20px; 
  border: 1px solid var(--border-subtle);
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 8px 16px rgba(0,0,0,0.02);
  position: relative;
}
.kpi-card:hover {
  transform: translateY(-4px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0,0,0,0.08), 0 0 0 1px var(--brand) inset;
}
```

### 3.2 Magnetic Data Tables
Tables should no longer be boring grids. Rows act as interactive links. 
- Use `padding: 16px 24px` for cells.
- The row itself scales and indents when hovered.
- An animated arrow (`→`) slides in from the right to indicate clickability.

**CSS Implementation:**
```css
.table-card {
  border-radius: 20px;
  background: var(--surface-1);
  box-shadow: 0 8px 24px rgba(0,0,0,0.03);
}
tr.main-row {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  cursor: pointer;
}
tr.main-row::after {
  content: '→';
  position: absolute; right: 24px; top: 50%; transform: translateY(-50%) translateX(-10px);
  color: var(--brand); font-weight: 900; font-size: 18px;
  opacity: 0; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
tr.main-row:hover {
  background: var(--surface-hover);
  transform: scale(1.01) translateX(4px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  border-radius: 12px;
}
tr.main-row:hover::after {
  opacity: 1; transform: translateY(-50%) translateX(0);
}
```

### 3.3 Dynamic Status Badges (Pills)
Instead of solid blocks of color, use a 10% opacity background of the target color with a solid color text. This looks far more modern and prevents the UI from becoming visually overwhelming.

**Example Implementation:**
```css
.status-badge {
  display: inline-flex; align-items: center; padding: 4px 10px; 
  border-radius: 6px; font-size: 11px; font-weight: 800; 
  text-transform: uppercase; letter-spacing: 0.05em;
}
/* Resolus (Green) */
.status-badge.resolu { background: rgba(16,185,129,0.1); color: #10b981; }
/* En cours (Orange) */
.status-badge.en_cours { background: rgba(245,158,11,0.1); color: #f59e0b; }
```

### 3.4 Page Load Animations
Elements should not instantly appear; they should cascade into view.
Always include these keyframes at the top of the stylesheet and apply them to major structural containers:

```css
@keyframes slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Usage */
.reports-hero { animation: fade-in-up 0.5s ease-out; }
.kpi-grid { animation: slide-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both 0.1s; }
.table-card { animation: slide-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both 0.2s; }
```

## 4. Reusing this Design
When updating a new page (e.g., `inbox.html` or the admin dashboard):
1. Wrap the main content in a container with padding (e.g., `.reports-page`).
2. Build the Hero header section using `.at-hero` styles.
3. Replace all standard tables with the `.table-card` and `.agents-table` classes defined above.
4. Replace raw text statuses with the `.status-badge` pills.
5. Inject the `@keyframes` block to ensure the page glides smoothly into view upon load.

---

## Mise à jour 2.4.0 — conventions front-end liées à la sécurité

- **Formulaires POST** : le jeton CSRF est ajouté automatiquement par `static/js/csrf.js` (champ caché `csrf_token` et en-tête `X-CSRFToken` pour `fetch`/XHR). Un formulaire créé dynamiquement n'a rien à faire de plus.
- **Données serveur dans du JavaScript** : ne jamais écrire `onclick="fn('{{ valeur }}')"`. Utiliser `onclick="fn({{ valeur|tojson|forceescape }})"`. Dans le JS client, échapper tout texte injecté via `innerHTML` (fonction `esc()` de la messagerie) ou utiliser `textContent`.
- **Déconnexion** : bouton dans un formulaire `POST` (icône de la barre supérieure), plus un lien.
- **Pages d'erreur** : `errors/400.html`, `403.html`, `404.html`, `413.html`, `500.html` (même gabarit centré : titre, explication, bouton de retour).
- **Statut « Ouvert »** : regroupe les statuts `nouveau` et `ouvert` dans les compteurs et filtres.
- **Listes de choix pilotées par la base** (catégories de PDV, palette de thèmes) : ne pas les écrire dans les gabarits ; les lire via `services/referentiels.py` (`get_categories()`, `get_themes()`, cache vidé par `invalidate()`). Elles sont stockées en JSON dans `configurations_systeme`. Les icônes de catégorie sont des clés (champ `icone` de chaque catégorie) dessinées par le macro `templates/pdv/_icons.html`.
- **Info-bulles d'aide** : `{% from '_macros.html' import info_tip %}` puis `{{ info_tip("texte") }}` à côté d'un libellé. La bulle est affichée par `static/js/tooltip.js` dans un calque flottant (jamais rognée par un parent en `overflow: hidden`, y compris dans un `<dialog>`). Les textes SLA sont centralisés dans `SLA_TIPS` (`templates/_macros.html`).
- **Styles dans un gabarit enfant** : tout `<style>` / `<script>` doit se trouver DANS un `{% block %}` ; hors bloc, Jinja l'ignore silencieusement.
- **Champs vides** : dans un `value="..."`, écrire `{{ (obj.champ if obj else '')|default('', true) }}` pour ne pas afficher « None ».


## Mise à jour 2.7.0 — affichage téléphone / tablette
- `static/css/mobile.css` est chargé **en dernier** (après `{% block extra_head %}`) : il corrige les pages qui n'ont pas de version mobile, avec `!important` quand une règle de page l'emporterait.
- Seuils : 1024 px (menu latéral en tiroir, bouton `#mobile-nav-toggle`), 768 px (téléphone), 480 px (petit téléphone).
- Le tiroir cible `#sidebar` (et non `.sidebar` : la page Ticket réutilise cette classe pour son panneau de droite).
- Tableaux : défilement horizontal automatique ; ajouter la classe `no-scroll` à un `<table>` pour l'en exclure.
- Champs de formulaire à 16 px sur téléphone (évite le zoom automatique d'iOS).
- Nouvelle page : prévoir un `@media (max-width: 768px)` pour ses grilles propres, ou réutiliser une classe déjà listée dans `mobile.css`.
