"""
Helpers de sécurité : protection CSRF, redirections sûres, échappement LIKE,
en-têtes HTTP de sécurité et contrôle d'accès aux fichiers uploadés.
"""
import hmac
import re
import secrets
from urllib.parse import urlparse

from flask import abort, current_app, jsonify, render_template, request, session
from flask_login import current_user

CSRF_SESSION_KEY = '_csrf_token'
SAFE_METHODS = {'GET', 'HEAD', 'OPTIONS', 'TRACE'}
HEX_COLOR_RE = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')
LOOPBACK_HOSTS = {'127.0.0.1', 'localhost', '::1', '[::1]'}


# ── CSRF ────────────────────────────────────────────────────────────────────
def generate_csrf_token():
    """Retourne (et crée si besoin) le jeton CSRF de la session courante."""
    token = session.get(CSRF_SESSION_KEY)
    if not token:
        token = secrets.token_urlsafe(32)
        session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token():
    session.pop(CSRF_SESSION_KEY, None)


def _wants_json():
    return (
        request.is_json
        or request.path.startswith('/api/')
        or '/api/' in request.path
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or 'application/json' in (request.headers.get('Accept') or '')
    )


def init_csrf(app):
    """Active la protection CSRF sur toutes les requêtes non sûres (POST/PUT/PATCH/DELETE)."""
    app.jinja_env.globals['csrf_token'] = generate_csrf_token

    @app.before_request
    def _csrf_protect():
        if not app.config.get('CSRF_ENABLED', True):
            return None
        if request.method in SAFE_METHODS:
            return None
        sent = (
            request.headers.get('X-CSRFToken')
            or request.headers.get('X-CSRF-Token')
            or request.form.get('csrf_token')
        )
        expected = session.get(CSRF_SESSION_KEY)
        if not expected or not sent or not hmac.compare_digest(str(expected), str(sent)):
            app.logger.warning('CSRF rejeté: %s %s', request.method, request.path)
            if _wants_json():
                return jsonify({'success': False, 'error': 'Jeton CSRF invalide ou expiré. Rechargez la page.'}), 400
            return render_template('errors/400.html'), 400
        return None


# ── Redirections ────────────────────────────────────────────────────────────
def is_safe_redirect(target):
    """Vrai si `target` est un chemin local (pas d'open redirect)."""
    if not target:
        return False
    target = target.strip()
    if not target.startswith('/') or target.startswith('//') or target.startswith('/\\'):
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


# ── Divers ──────────────────────────────────────────────────────────────────
def like_escape(value):
    """Échappe %, _ et \\ pour un usage dans ILIKE ... ESCAPE '\\'."""
    return (value or '').replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def is_hex_color(value):
    return bool(value and HEX_COLOR_RE.match(value))


def safe_color(value, default):
    return value if is_hex_color(value) else default


def is_loopback(host):
    return (host or '').strip().lower() in LOOPBACK_HOSTS


def csv_safe(value):
    """Neutralise l'injection de formules dans les exports CSV/Excel."""
    if isinstance(value, str) and value and value[0] in ('=', '+', '-', '@', '\t', '\r'):
        return "'" + value
    return value


def parse_int(value, default, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    if minimum is not None and number < minimum:
        return default
    if maximum is not None and number > maximum:
        return default
    return number


# ── En-têtes et accès aux uploads ───────────────────────────────────────────
def init_security_headers(app):
    @app.before_request
    def _protect_uploads():
        # Les fichiers uploadés (pièces jointes, photos) ne sont servis qu'aux utilisateurs connectés.
        if request.path.startswith('/static/uploads/') and not current_user.is_authenticated:
            abort(401)

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
        resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if request.path.startswith('/static/uploads/'):
            # Neutralise tout contenu actif (HTML/SVG/JS) qui aurait été uploadé.
            resp.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'"
            resp.headers['Cache-Control'] = 'private, max-age=3600'
        if app.config.get('SESSION_COOKIE_SECURE'):
            resp.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        return resp
