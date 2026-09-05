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

fail() {
  log "FOUT: $*"
  printf '%s\n' "FOUT: $*" >&2
  exit 1
}

log "Updater gestart"
log "Webmap: $WEB_DIR"
log "Datamap: $DATA_DIR"

download() {
  url="$1"
  dest="$2"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$dest"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO "$dest" "$url"
  else
    fail "curl en wget ontbreken."
  fi
}

TMP_DIR="$(mktemp -d /tmp/machinepark-update.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT INT TERM

META_FILE="$TMP_DIR/deploy-meta.json"
log "Versie-informatie ophalen van GitHub"
if ! download "$META_URL" "$META_FILE"; then
  fail "deploy-meta.json kon niet van GitHub worden gedownload."
fi

REMOTE_SHA="$(sed -n 's/.*"source_sha"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$META_FILE" | head -n 1)"
if [ -z "$REMOTE_SHA" ]; then
  fail "source_sha kon niet uit deploy-meta.json worden gelezen."
fi

log "Beschikbare versie: $REMOTE_SHA"

LOCAL_SHA=""
if [ -f "$STATE_FILE" ]; then
  LOCAL_SHA="$(cat "$STATE_FILE" 2>/dev/null || true)"
fi

if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
  log "Geen update nodig: $REMOTE_SHA"
  exit 0
fi

ARCHIVE="$TMP_DIR/deploy.tar.gz"
log "Nieuwe programmaversie downloaden"
if ! download "$ARCHIVE_URL" "$ARCHIVE"; then
  fail "GitHub-archief kon niet worden gedownload."
fi
if ! tar -xzf "$ARCHIVE" -C "$TMP_DIR"; then
  fail "GitHub-archief kon niet worden uitgepakt."
fi

SOURCE_DIR=""
for candidate in "$TMP_DIR"/machinepark-*; do
  if [ -d "$candidate" ] && [ -f "$candidate/index.html" ]; then
    SOURCE_DIR="$candidate"
    break
  fi
done

if [ -z "$SOURCE_DIR" ]; then
  log "Inhoud tijdelijke map:"
  for candidate in "$TMP_DIR"/*; do
    [ -e "$candidate" ] || continue
    log " - $candidate"
  done
  fail "gedownloade Synology-build is ongeldig of index.html werd niet gevonden."
fi

log "Uitgepakte programmamap: $SOURCE_DIR"

# Eén terugvalkopie bewaren van de huidige webapp.
if [ -d "$WEB_DIR" ] && [ -f "$WEB_DIR/index.html" ]; then
  rm -f "$BACKUP_FILE"
  tar -czf "$BACKUP_FILE" -C "$WEB_DIR" . || {
    log "FOUT: backup van huidige webapp mislukt."
    exit 1
  }
fi

mkdir -p "$WEB_DIR"
if [ ! -d "$WEB_DIR" ] || [ ! -w "$WEB_DIR" ]; then
  fail "webmap bestaat niet of is niet schrijfbaar: $WEB_DIR"
fi

# Alleen programmabestanden worden bijgewerkt.
# /volume1/MachineparkData wordt nooit aangeraakt of verwijderd.
if ! cp -R "$SOURCE_DIR"/. "$WEB_DIR"/; then
  fail "programmabestanden konden niet naar $WEB_DIR worden gekopieerd."
fi

printf '%s' "$REMOTE_SHA" > "$STATE_FILE"
log "Machinepark bijgewerkt naar $REMOTE_SHA"
log "Updater klaar"
