#!/usr/bin/env bash
# ===================================================================
# Feasto — kunlik zaxira (baza + yuklangan fayllar)
#
# Joyi:  /srv/feasto/deploy/backup.sh
# Ishga: systemd timer (feasto-backup.timer) har kuni 03:30 da
#
# Nega faqat baza emas: bron va foydalanuvchi ma'lumoti bazada, LEKIN
# joy rasmlari va avatarlar fayl tizimida. Bazani tiklab, rasmlarni
# yo'qotsak, sayt bo'm-bo'sh kartochkalar bilan ochiladi.
# ===================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/srv/backups/feasto}"
KEEP_DAYS="${KEEP_DAYS:-14}"
STAMP="$(date +%Y-%m-%d_%H%M)"

# .env dan baza ma'lumotini o'qiymiz — parol skriptda yozilmaydi.
set -a
# shellcheck disable=SC1091
source /srv/feasto/.env
set +a

mkdir -p "$BACKUP_DIR"

# --- baza ---
# `--clean` — tiklashda eski jadvallarni o'zi tozalaydi.
PGPASSWORD="$DB_PASSWORD" pg_dump \
    --host="$DB_HOST" --port="$DB_PORT" \
    --username="$DB_USER" --dbname="$DB_NAME" \
    --format=custom --clean --if-exists \
    --file="$BACKUP_DIR/db_$STAMP.dump"

# --- yuklangan fayllar ---
tar --create --gzip \
    --file="$BACKUP_DIR/media_$STAMP.tar.gz" \
    --directory=/srv/feasto media

# --- eskilarini tozalash ---
find "$BACKUP_DIR" -name 'db_*.dump'      -mtime "+$KEEP_DAYS" -delete
find "$BACKUP_DIR" -name 'media_*.tar.gz' -mtime "+$KEEP_DAYS" -delete

# Zaxira BOSHQA joyda ham turishi kerak: server diski yonsa, undagi
# zaxira ham yonadi. Quyidagi qatorni o'zingizning S3/MinIO yoki
# boshqa serveringizga moslab oching.
# rclone copy "$BACKUP_DIR" remote:feasto-backups --max-age 25h

echo "Zaxira tayyor: $BACKUP_DIR/db_$STAMP.dump"
