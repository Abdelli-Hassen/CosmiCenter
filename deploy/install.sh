#!/usr/bin/env bash
# ============================================================================
#  CosmiCenter — installateur / mise à jour automatique pour Ubuntu 22.04+
#
#  Usage (depuis le dossier du projet, sur le serveur) :
#       sudo bash deploy/install.sh
#
#  1re exécution = installation complète. Les exécutions suivantes = mise à jour
#  (le code est recopié, les dépendances mises à jour, le service redémarré ;
#  la base de données, le .env et les fichiers envoyés ne sont jamais touchés).
#
#  Variables facultatives (pour une exécution sans question) :
#       DOMAIN=support.exemple.com EMAIL=moi@exemple.com \
#       DUMP_FILE=~/cosmicenter.sql UPLOADS_ARCHIVE=~/uploads.tar.gz \
#       OLD_SECRET_KEY=... sudo -E bash deploy/install.sh
#
#  Les chemins de fichiers peuvent s'écrire « ~/fichier » (dossier personnel) ou relativement au dossier
#  d'où vous lancez le script. Dossier d'installation modifiable : APP_DIR=/autre/dossier sudo -E bash deploy/install.sh
# ============================================================================
set -Eeuo pipefail

APP_NAME="cosmicenter"
APP_DIR="${APP_DIR:-/opt/cosmicenter}"
APP_USER="cosmicenter"
APP_PORT="8080"
DB_NAME="cosmicenter"
DB_USER="cosmicenter"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/cosmicenter}"
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── petits utilitaires d'affichage ──────────────────────────────────────────
C_RESET=$'\e[0m'; C_GREEN=$'\e[32m'; C_YELLOW=$'\e[33m'; C_RED=$'\e[31m'; C_BLUE=$'\e[36m'
step() { echo; echo "${C_BLUE}▶ $*${C_RESET}"; }
ok()   { echo "  ${C_GREEN}✔ $*${C_RESET}"; }
warn() { echo "  ${C_YELLOW}⚠ $*${C_RESET}"; }
die()  { echo "${C_RED}✗ $*${C_RESET}" >&2; exit 1; }
trap 'echo; echo "${C_RED}✗ L'"'"'installation s'"'"'est arrêtée à la ligne $LINENO. Lisez le message ci-dessus, corrigez, puis relancez la même commande (elle est sans danger à relancer).${C_RESET}"' ERR

# ── doit être root ──────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
  echo "Ce script a besoin des droits administrateur : relance avec sudo..."
  exec sudo -E bash "$0" "$@"
fi
START_DIR="$PWD"   # dossier d'où le script a été lancé (les chemins relatifs s'y rapportent)
cd /tmp

if [[ -r /etc/os-release ]]; then
  . /etc/os-release
  [[ "${ID:-}" == "ubuntu" ]] || warn "Système détecté : ${PRETTY_NAME:-inconnu}. Ce script est prévu pour Ubuntu ; ça peut quand même fonctionner sous Debian."
fi

UPDATE=0
[[ -f "$APP_DIR/.env" ]] && UPDATE=1

SERVER_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
SERVER_IP="${SERVER_IP:-localhost}"
INTERACTIVE=0
[[ -t 0 ]] && INTERACTIVE=1

echo "============================================================"
echo "   CosmiCenter — $([[ $UPDATE -eq 1 ]] && echo 'MISE À JOUR' || echo 'INSTALLATION')"
echo "============================================================"

# ── questions (installation uniquement) ─────────────────────────────────────
DOMAIN="${DOMAIN:-}"; EMAIL="${EMAIL:-}"; DUMP_FILE="${DUMP_FILE:-}"; UPLOADS_ARCHIVE="${UPLOADS_ARCHIVE:-}"; OLD_SECRET_KEY="${OLD_SECRET_KEY:-}"
if [[ $UPDATE -eq 0 && $INTERACTIVE -eq 1 ]]; then
  echo
  echo "Quelques questions (appuyez sur Entrée pour passer une question) :"
  [[ -z "$DOMAIN" ]] && read -rp "1) Nom de domaine du site (ex: support.exemple.com). Vide = on utilisera l'adresse IP en HTTP : " DOMAIN
  if [[ -n "$DOMAIN" && -z "$EMAIL" ]]; then
    read -rp "2) Votre e-mail (pour le certificat HTTPS gratuit) : " EMAIL
  fi
  [[ -z "$DUMP_FILE" ]] && read -rp "3) Fichier de sauvegarde de la base (.sql) venant de votre PC, ex: ~/cosmicenter.sql. Vide = base neuve : " DUMP_FILE
  if [[ -n "$DUMP_FILE" && -z "$OLD_SECRET_KEY" ]]; then
    read -rp "4) SECRET_KEY de l'ancien fichier .env (nécessaire pour relire les mots de passe AnyDesk/TeamViewer déjà enregistrés). Vide = nouvelle clé : " OLD_SECRET_KEY
  fi
  [[ -z "$UPLOADS_ARCHIVE" ]] && read -rp "5) Archive des fichiers envoyés (.tar.gz) venant de votre PC, ex: ~/uploads.tar.gz. Vide = aucune : " UPLOADS_ARCHIVE
fi

# « ~/fichier » = dossier personnel de l'utilisateur ; « fichier » = relatif au dossier de lancement
resolve_path() {
  local p="$1" home_dir
  [[ -z "$p" ]] && return 0
  home_dir="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"
  case "$p" in
    "~")   p="$home_dir" ;;
    "~/"*) p="$home_dir/${p#\~/}" ;;
    /*)    ;;
    *)     p="$START_DIR/$p" ;;
  esac
  echo "$p"
}
DUMP_FILE="$(resolve_path "$DUMP_FILE")"
UPLOADS_ARCHIVE="$(resolve_path "$UPLOADS_ARCHIVE")"

[[ -n "$DUMP_FILE" && ! -f "$DUMP_FILE" ]] && die "Fichier de base introuvable : $DUMP_FILE"
[[ -n "$UPLOADS_ARCHIVE" && ! -f "$UPLOADS_ARCHIVE" ]] && die "Archive introuvable : $UPLOADS_ARCHIVE"
[[ -n "$DOMAIN" && -z "$EMAIL" ]] && warn "Pas d'e-mail fourni : le HTTPS ne sera pas configuré automatiquement."

IS_IP=0
[[ "$DOMAIN" =~ ^[0-9.]+$ ]] && IS_IP=1
PUBLIC_HOST="${DOMAIN:-$SERVER_IP}"

# ── 1. logiciels ────────────────────────────────────────────────────────────
step "1/9  Installation des logiciels (Python, PostgreSQL, Nginx...)"
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a   # Ubuntu 22.04+ : évite la question « services à redémarrer » pendant apt
apt-get update -y -qq
PKGS=(python3 python3-venv python3-pip git rsync postgresql libpq-dev nginx ufw curl openssl cron)
if [[ -n "$DOMAIN" && $IS_IP -eq 0 && -n "$EMAIL" ]]; then PKGS+=(certbot python3-certbot-nginx); fi
apt-get install -y -qq "${PKGS[@]}"
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' || die "Python 3.10 ou plus récent est nécessaire (Ubuntu 22.04 ou 24.04)."
ok "Logiciels installés ($(python3 --version))"

# ── 2. utilisateur système + code ───────────────────────────────────────────
step "2/9  Copie de l'application dans $APP_DIR"
id -u "$APP_USER" &>/dev/null || useradd --system --create-home --home-dir "/home/$APP_USER" --shell /usr/sbin/nologin "$APP_USER"
mkdir -p "$APP_DIR"
if [[ "$SRC_DIR" != "$APP_DIR" ]]; then
  # Exclus : environnement Python, secrets, données et fichiers inutiles (ou dangereux) en production.
  rsync -a --delete \
    --exclude 'venv/' --exclude '.git/' --exclude '__pycache__/' --exclude '*.pyc' \
    --exclude '.env' --exclude 'logs/' --exclude 'instance/' --exclude 'static/uploads/' \
    --exclude 'scratch/' --exclude 'tests/' --exclude '*.xlsx' --exclude '*.csv' --exclude 'seed_db.py' \
    "$SRC_DIR"/ "$APP_DIR"/
fi
mkdir -p "$APP_DIR/logs" "$APP_DIR/instance" "$APP_DIR/static/uploads/tickets" "$APP_DIR/static/uploads/profiles"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
ok "Code copié"

# ── 3. environnement Python ─────────────────────────────────────────────────
step "3/9  Environnement Python et dépendances (1 à 3 minutes)"
[[ -x "$APP_DIR/venv/bin/python" ]] || sudo -u "$APP_USER" python3 -m venv "$APP_DIR/venv"
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet --upgrade pip wheel
sudo -u "$APP_USER" "$APP_DIR/venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"
ok "Dépendances installées"

# ── 4. base de données + configuration (installation seulement) ─────────────
if [[ $UPDATE -eq 0 ]]; then
  step "4/9  Base de données PostgreSQL et fichier de configuration"
  systemctl enable --now postgresql >/dev/null 2>&1
  DB_PASS="$(openssl rand -hex 16)"
  sudo -u postgres psql -v ON_ERROR_STOP=1 -q <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
    CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';
  ELSE
    ALTER ROLE $DB_USER PASSWORD '$DB_PASS';
  END IF;
END
\$\$;
SQL
  sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
    || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

  SECRET_KEY="${OLD_SECRET_KEY:-$(openssl rand -hex 32)}"
  SCHEME="http"
  cat > "$APP_DIR/.env" <<ENV
# Généré par deploy/install.sh — ne jamais partager ni publier ce fichier.
FLASK_APP=app.py
FLASK_ENV=production
FLASK_DEBUG=False
FLASK_HOST=127.0.0.1
FLASK_PORT=$APP_PORT
BEHIND_PROXY=true

SECRET_KEY=$SECRET_KEY
DATABASE_URL=postgresql://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME

UPLOAD_FOLDER=static/uploads
SESSION_COOKIE_SECURE=false
PUBLIC_BASE_URL=$SCHEME://$PUBLIC_HOST

MAX_LOGIN_ATTEMPTS=7
LOCKOUT_DURATION_MINUTES=30
TIMEZONE=Africa/Tunis
SUPPORT_EMAIL=support@example.com

# E-mail sortant : à renseigner ensuite depuis le site (Administration > Paramètres Système) ou ici.
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USE_SSL=False
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=noreply@example.com

IMAP_ENABLE_POLLING=false
ENV
  chown "$APP_USER:$APP_USER" "$APP_DIR/.env"; chmod 600 "$APP_DIR/.env"
  ok "Base '$DB_NAME' et fichier .env créés (mots de passe générés automatiquement)"

  if [[ -n "$DUMP_FILE" ]]; then
    step "     Restauration de votre base depuis $DUMP_FILE"
    PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -q -v ON_ERROR_STOP=0 -f "$DUMP_FILE" >/tmp/cosmicenter-restore.log 2>&1 \
      || warn "La restauration a signalé des erreurs (voir /tmp/cosmicenter-restore.log)."
    ok "Base restaurée"
  fi
  if [[ -n "$UPLOADS_ARCHIVE" ]]; then
    tar -xzf "$UPLOADS_ARCHIVE" -C "$APP_DIR"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR/static" "$APP_DIR/instance"
    ok "Fichiers envoyés restaurés"
  fi
else
  step "4/9  Mise à jour : configuration et base de données conservées"
  ok ".env et base de données inchangés"
fi

# ── 5. création / mise à jour des tables ────────────────────────────────────
step "5/9  Préparation des tables de la base"
( cd "$APP_DIR" && sudo -u "$APP_USER" "$APP_DIR/venv/bin/python" -c "from app import create_app; create_app('production')" ) >/tmp/cosmicenter-init.log 2>&1 \
  || { cat /tmp/cosmicenter-init.log; die "L'application ne démarre pas (voir ci-dessus)."; }
ok "Tables prêtes"

FIRST_LOGIN_FILE="/root/cosmicenter-first-login.txt"
if [[ $UPDATE -eq 0 ]]; then
  set -a; . "$APP_DIR/.env"; set +a
  USERS="$(psql "$DATABASE_URL" -tAc 'select count(*) from utilisateurs' 2>/dev/null || echo 0)"
  if [[ "${USERS:-0}" == "0" ]]; then
    ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | cut -c1-14)"
    ( cd "$APP_DIR" && ADMIN_PASSWORD="$ADMIN_PASSWORD" sudo -E -u "$APP_USER" "$APP_DIR/venv/bin/python" -m flask --app app init-db ) >/tmp/cosmicenter-admin.log 2>&1 \
      || { cat /tmp/cosmicenter-admin.log; die "Impossible de créer le compte administrateur."; }
    printf 'Adresse : %s\nCompte  : admin@example.com\nMot de passe : %s\n(Changez ce mot de passe dès la première connexion, puis supprimez ce fichier.)\n' \
      "$SCHEME://$PUBLIC_HOST" "$ADMIN_PASSWORD" > "$FIRST_LOGIN_FILE"
    chmod 600 "$FIRST_LOGIN_FILE"
    ok "Compte administrateur créé (identifiants dans $FIRST_LOGIN_FILE)"
  else
    ok "$USERS utilisateurs déjà présents : aucun compte créé"
  fi
fi

# ── 6. service systemd ──────────────────────────────────────────────────────
step "6/9  Service de démarrage automatique"
cat > "/etc/systemd/system/$APP_NAME.service" <<UNIT
[Unit]
Description=CosmiCenter (application web)
After=network.target postgresql.service

[Service]
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/python serve.py
Restart=always
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable "$APP_NAME" >/dev/null 2>&1
systemctl restart "$APP_NAME"
ok "Service '$APP_NAME' démarré"

# ── 7. Nginx + pare-feu (installation seulement) ────────────────────────────
if [[ $UPDATE -eq 0 ]]; then
  step "7/9  Serveur web Nginx et pare-feu"
  SERVER_NAME="${DOMAIN:-_}"
  cat > "/etc/nginx/sites-available/$APP_NAME" <<'NGINX'
server {
    listen 80;
    server_name __SERVER_NAME__;

    client_max_body_size 50m;          # l'application accepte jusqu'à 50 Mo par envoi

    location / {
        proxy_pass http://127.0.0.1:__APP_PORT__;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 60s;
    }
}
NGINX
  sed -i "s/__SERVER_NAME__/$SERVER_NAME/; s/__APP_PORT__/$APP_PORT/" "/etc/nginx/sites-available/$APP_NAME"
  ln -sf "/etc/nginx/sites-available/$APP_NAME" "/etc/nginx/sites-enabled/$APP_NAME"
  rm -f /etc/nginx/sites-enabled/default
  nginx -t
  systemctl enable --now nginx >/dev/null 2>&1
  systemctl reload nginx
  ok "Nginx configuré"

  SSH_PORT="$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')"; SSH_PORT="${SSH_PORT:-22}"
  ufw allow "$SSH_PORT/tcp" >/dev/null
  ufw allow 'Nginx Full' >/dev/null
  ufw --force enable >/dev/null
  ok "Pare-feu actif : ports $SSH_PORT (SSH), 80 et 443 uniquement"
fi

# ── 8. HTTPS (installation seulement) ───────────────────────────────────────
if [[ $UPDATE -eq 0 ]]; then
  step "8/9  HTTPS (certificat gratuit Let's Encrypt)"
  if [[ -n "$DOMAIN" && $IS_IP -eq 0 && -n "$EMAIL" ]]; then
    if certbot --nginx -d "$DOMAIN" -m "$EMAIL" --agree-tos --no-eff-email --non-interactive --redirect; then
      sed -i 's/^SESSION_COOKIE_SECURE=.*/SESSION_COOKIE_SECURE=true/' "$APP_DIR/.env"
      sed -i "s#^PUBLIC_BASE_URL=.*#PUBLIC_BASE_URL=https://$DOMAIN#" "$APP_DIR/.env"
      [[ -f "$FIRST_LOGIN_FILE" ]] && sed -i "s#^Adresse : .*#Adresse : https://$DOMAIN#" "$FIRST_LOGIN_FILE"
      systemctl restart "$APP_NAME"
      SCHEME="https"
      ok "HTTPS activé pour $DOMAIN (renouvellement automatique)"
    else
      warn "Le certificat n'a pas pu être obtenu (le domaine pointe-t-il bien vers ce serveur ?). Le site reste en HTTP. Relancez plus tard : sudo certbot --nginx -d $DOMAIN"
    fi
  else
    warn "Pas de domaine/e-mail : le site fonctionne en HTTP. Ajoutez un domaine pour activer HTTPS (voir le guide)."
  fi
fi

# ── 9. sauvegardes automatiques ─────────────────────────────────────────────
step "9/9  Sauvegardes automatiques quotidiennes"
install -m 755 "$APP_DIR/deploy/backup.sh" /usr/local/bin/cosmicenter-backup
mkdir -p "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"
echo "30 2 * * * root APP_DIR=$APP_DIR BACKUP_DIR=$BACKUP_DIR /usr/local/bin/cosmicenter-backup >> /var/log/cosmicenter-backup.log 2>&1" > /etc/cron.d/cosmicenter-backup
chmod 644 /etc/cron.d/cosmicenter-backup
ok "Sauvegarde chaque nuit à 02:30 dans $BACKUP_DIR (14 jours conservés)"

# ── vérification finale ─────────────────────────────────────────────────────
step "Vérification"
sleep 3
if curl -fsS "http://127.0.0.1:$APP_PORT/api/health" >/dev/null; then
  ok "L'application répond correctement"
else
  journalctl -u "$APP_NAME" -n 30 --no-pager || true
  die "L'application ne répond pas (voir les logs ci-dessus)."
fi

echo
echo "${C_GREEN}============================================================${C_RESET}"
echo "${C_GREEN}  ✔ TERMINÉ${C_RESET}"
if [[ $UPDATE -eq 0 ]]; then
  echo "  Votre site : ${SCHEME:-http}://$PUBLIC_HOST"
  [[ -f "$FIRST_LOGIN_FILE" ]] && echo "  Identifiants du premier compte : sudo cat $FIRST_LOGIN_FILE"
  echo "  Étape suivante : connectez-vous, changez le mot de passe,"
  echo "  puis testez l'e-mail (Administration > Paramètres Système)."
else
  echo "  Mise à jour terminée : le site tourne avec la nouvelle version."
fi
echo "  Aide : voir DEPLOYMENT_GUIDE.md (état : sudo systemctl status $APP_NAME)"
echo "${C_GREEN}============================================================${C_RESET}"
