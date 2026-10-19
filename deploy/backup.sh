#!/usr/bin/env bash
# CosmiCenter — sauvegarde : base de données + fichiers envoyés (pièces jointes, photos, fichiers de messagerie).
# Installé par deploy/install.sh dans /usr/local/bin/cosmicenter-backup et lancé chaque nuit à 02:30.
# Lancement manuel :  sudo cosmicenter-backup
set -Eeuo pipefail

APP_DIR="/opt/cosmicenter"
BACKUP_DIR="/var/backups/cosmicenter"
KEEP_DAYS=14
STAMP="$(date +%Y%m%d-%H%M)"

mkdir -p "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"

DATABASE_URL="$(grep -E '^DATABASE_URL=' "$APP_DIR/.env" | head -n1 | cut -d= -f2-)"
[[ -n "$DATABASE_URL" ]] || { echo "DATABASE_URL introuvable dans $APP_DIR/.env" >&2; exit 1; }
DATABASE_URL="${DATABASE_URL/postgresql+psycopg:/postgresql:}"

pg_dump --no-owner --no-acl "$DATABASE_URL" | gzip > "$BACKUP_DIR/db-$STAMP.sql.gz"

tar -czf "$BACKUP_DIR/files-$STAMP.tar.gz" -C "$APP_DIR" \
  $( [[ -d "$APP_DIR/static/uploads" ]] && echo static/uploads ) \
  $( [[ -d "$APP_DIR/instance/chat_files" ]] && echo instance/chat_files )

find "$BACKUP_DIR" -type f \( -name 'db-*.sql.gz' -o -name 'files-*.tar.gz' \) -mtime +"$KEEP_DAYS" -delete
echo "$(date '+%F %T') sauvegarde OK : db-$STAMP.sql.gz + files-$STAMP.tar.gz"
