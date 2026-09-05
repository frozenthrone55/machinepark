#!/bin/sh
set -eu

DATA_DIR="/volume1/MachineparkData"
UPDATER="$DATA_DIR/update-from-github.sh"
LOG_FILE="$DATA_DIR/backups/task-output.log"
CACHE_BUST="$(date +%s)"
UPDATER_URL="https://raw.githubusercontent.com/frozenthrone55/machinepark/synology-selfhost/synology/update-from-github.sh?machinepark=$CACHE_BUST"

mkdir -p "$DATA_DIR/backups"
exec >> "$LOG_FILE" 2>&1

echo "===== Machinepark update gestart: $(date) ====="
echo "Updater opnieuw ophalen met cache-buster: $CACHE_BUST"

if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$UPDATER_URL" -o "$UPDATER"
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$UPDATER" "$UPDATER_URL"
else
    echo "FOUT: curl en wget zijn niet beschikbaar"
    exit 1
fi

if [ ! -s "$UPDATER" ]; then
    echo "FOUT: updater is leeg of kon niet worden opgehaald"
    exit 1
fi

/bin/sh "$UPDATER"

echo "===== Machinepark update klaar: $(date) ====="
