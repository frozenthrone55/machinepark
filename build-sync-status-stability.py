from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
text = path.read_text(encoding='utf-8')

MARKER = '// machinepark-sync-status-stability-v1'

if MARKER not in text:
    old_dirty = """        if (meta.dirty) {
          bind();
          await refresh();
          centralSync.enabled = true;
          startCentralPolling();
          setCentralSyncStatus('☁ Verbinding hersteld · lokale wijzigingen synchroniseren…', 'busy');
          const pushed = await centralPush({ initial: true });
          if (!pushed?.offline) await centralPull({ apply: true, quiet: true });
          await refreshOnlineExtras();
          return;
        }"""

    new_dirty = """        if (meta.dirty) {
          // machinepark-sync-status-stability-v1
          // Lokale wijzigingen mogen de appstart nooit blokkeren. Open eerst
          // de lokale gegevens en probeer de centrale push daarna best-effort.
          bind();
          await refresh();
          centralSync.enabled = true;
          startCentralPolling();
          setCentralSyncStatus('☁ Lokale wijzigingen wachten op synchronisatie', 'busy');
          try {
            const pushed = await centralPush({ initial: true });
            if (!pushed?.offline) {
              await centralPull({ apply: true, quiet: true });
              await refreshOnlineExtras();
            } else {
              setOfflineStatus();
            }
          } catch (error) {
            console.warn('Opstartsynchronisatie mislukt; lokale gegevens blijven actief', error);
            const message = String(error?.message || error || '').replace(/\\s+/g, ' ').trim().slice(0, 140);
            setCentralSyncStatus(
              message ? '☁ Synchronisatie wacht op controle · ' + message : '☁ Synchronisatie wacht op controle',
              'error'
            );
          }
          return;
        }"""

    if text.count(old_dirty) != 1:
        raise SystemExit(f'Sync stabiliteit: dirty-startup verwacht 1x, gevonden {text.count(old_dirty)}x')
    text = text.replace(old_dirty, new_dirty, 1)

    old_alert = """        window.__koffieServiceStarted = false;
        console.error(error);
        alert('Machinepark kon niet worden gestart. De lokale gegevens zijn niet aangepast.');"""
    new_alert = """        window.__koffieServiceStarted = false;
        console.error(error);
        const startupMessage = String(error?.message || error || '').replace(/\\s+/g, ' ').trim().slice(0, 180);
        alert(
          startupMessage
            ? 'Machinepark kon niet worden gestart: ' + startupMessage
            : 'Machinepark kon niet worden gestart. De lokale gegevens zijn niet aangepast.'
        );"""
    if old_alert in text:
        text = text.replace(old_alert, new_alert, 1)

    path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
required = [
    MARKER,
    'Lokale wijzigingen mogen de appstart nooit blokkeren',
    'Opstartsynchronisatie mislukt; lokale gegevens blijven actief',
    "message ? '☁ Synchronisatie wacht op controle · ' + message",
    'let pushFailed = false',
    'pushFailed = true',
    'if (!pushFailed && centralSync.pending && centralSync.enabled && navigator.onLine)',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: sync-stabiliteit ontbreekt ({needle})')

print('[Machinepark] synchronisatiefouten blokkeren de appstart niet en veroorzaken geen snelle retrylus')
