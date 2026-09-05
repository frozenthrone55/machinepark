#!/bin/sh
set -eu

REPO="frozenthrone55/machinepark"
BRANCH="synology-deploy"
WEB_DIR="/volume1/web/machinepark"
DATA_DIR="/volume1/MachineparkData"
STATE_FILE="$DATA_DIR/data/.machinepark-deploy-sha"
LOG_FILE="$DATA_DIR/backups/synology-update.log"
BACKUP_FILE="$DATA_DIR/backups/machinepark-web-last-good.tar.gz"

META_URL="https://raw.githubusercontent.com/$REPO/$BRANCH/deploy-meta.json"
ARCHIVE_URL="https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH"

mkdir -p "$DATA_DIR/data" "$DATA_DIR/backups"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$LOG_FILE"
}

download() {
  url="$1"
  dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dest"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dest" "$url"
  else
    log "FOUT: curl en wget ontbreken."
    exit 1
  fi
}

TMP_DIR="$(mktemp -d /tmp/machinepark-update.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

META_FILE="$TMP_DIR/deploy-meta.json"
download "$META_URL" "$META_FILE"

REMOTE_SHA="$(sed -n 's/.*"source_sha"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)"
if [ -z "$REMOTE_SHA" ]; then
  log "FOUT: source_sha kon niet uit deploy-meta.json worden gelezen."
  exit 1
fi

LOCAL_SHA=""
if [ -f "$STATE_FILE" ]; then
  LOCAL_SHA="$(cat "$STATE_FILE" 2>/dev/null || true)"
fi

if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
  log "Geen update nodig: $REMOTE_SHA"
  exit 0
fi

ARCHIVE="$TMP_DIR/deploy.tar.gz"
download "$ARCHIVE_URL" "$ARCHIVE"
tar -xzf "$ARCHIVE" -C "$TMP_DIR"

SOURCE_DIR="$(find "$TMP_DIR" -maxdepth 1 -type d -name 'machinepark-*' | head -n 1)"
if [ -z "$SOURCE_DIR" ] || [ ! -f "$SOURCE_DIR/index.html" ]; then
  log "FOUT: gedownloade Synology-build is ongeldig."
  exit 1
fi

# Eén terugvalkopie bewaren van de huidige webapp.
if [ -d "$WEB_DIR" ] && [ -f "$WEB_DIR/index.html" ]; then
  rm -f "$BACKUP_FILE"
  tar -czf "$BACKUP_FILE" -C "$WEB_DIR" . || {
    log "FOUT: backup van huidige webapp mislukt."
    exit 1
  }
fi

mkdir -p "$WEB_DIR"

# Alleen programmabestanden worden bijgewerkt.
# /volume1/MachineparkData wordt nooit aangeraakt of verwijderd.
cp -R "$SOURCE_DIR"/. "$WEB_DIR"/

printf '%s' "$REMOTE_SHA" > "$STATE_FILE"
log "Machinepark bijgewerkt naar $REMOTE_SHA"
