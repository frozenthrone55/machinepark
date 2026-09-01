from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="auto-live-sync-v1"'

if MARKER not in index:
    feature = r'''
<script>
(() => {
  const LIVE_SYNC_INTERVAL_MS = 3000;
  let liveSyncTimer = null;
  let liveSyncRunning = false;

  async function machineparkLiveSyncNow() {
    if (liveSyncRunning) return;
    if (document.visibilityState === 'hidden') return;
    if (!navigator.onLine || !window.Clerk?.isSignedIn || !window.__koffieServiceStarted) return;

    liveSyncRunning = true;
    try {
      if (typeof window.machineparkSyncOnlineNow === 'function') {
        await window.machineparkSyncOnlineNow({ quiet: true });
      }

      // De storingsbibliotheek gebruikt een aparte centrale bron en moet daarom
      // naast de hoofddata afzonderlijk worden ververst.
      if (typeof window.machineparkLoadFaultLibrary === 'function') {
        await window.machineparkLoadFaultLibrary(true);
        if (typeof window.machineparkRenderFaultLibrary === 'function') {
          window.machineparkRenderFaultLibrary();
        }
      }
    } catch (error) {
      // De bestaande synchronisatielaag toont netwerk-/authfouten. De live poll
      // blijft stil zodat een tijdelijk netwerkprobleem geen herhaalde pop-ups geeft.
      console.warn('Automatische live synchronisatie', error);
    } finally {
      liveSyncRunning = false;
    }
  }

  function startMachineparkLiveSync() {
    if (liveSyncTimer) return;
    liveSyncTimer = setInterval(machineparkLiveSyncNow, LIVE_SYNC_INTERVAL_MS);
    setTimeout(machineparkLiveSyncNow, 250);
  }

  window.machineparkLiveSyncNow = machineparkLiveSyncNow;
  window.machineparkStartLiveSync = startMachineparkLiveSync;

  window.addEventListener('online', () => setTimeout(machineparkLiveSyncNow, 100));
  window.addEventListener('focus', () => setTimeout(machineparkLiveSyncNow, 100));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') setTimeout(machineparkLiveSyncNow, 100);
  });

  startMachineparkLiveSync();
})();
</script>
<span data-machinepark-build-fix="auto-live-sync-v1" hidden></span>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor live sync')
    index = index.replace('</body>', feature + '\n</body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'LIVE_SYNC_INTERVAL_MS = 3000',
    'window.machineparkSyncOnlineNow({ quiet: true })',
    'window.machineparkLoadFaultLibrary(true)',
    'window.machineparkRenderFaultLibrary()',
    "window.addEventListener('online'",
    "window.addEventListener('focus'",
    "document.addEventListener('visibilitychange'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: automatische live sync ontbreekt ({needle})')

print('[Machinepark] depannages, onderhoud en storingen verversen automatisch tussen toestellen')
