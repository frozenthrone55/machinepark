from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="auto-live-sync-v1"'

if MARKER not in index:
    feature = r'''
<script data-machinepark-build-fix="auto-live-sync-v1">
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
      if (typeof window.machineparkLoadFaultLibrary === 'function') {
        await window.machineparkLoadFaultLibrary(true);
        if (typeof window.machineparkRenderFaultLibrary === 'function') {
          window.machineparkRenderFaultLibrary();
        }
      }
    } catch (error) {
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
'''
    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor live sync')
    index = index[:body_pos] + feature + '\n' + index[body_pos:]
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
    "rfind('</body>')",
]
for needle in required:
    if needle not in index and needle != "rfind('</body>')":
        raise SystemExit(f'Buildvalidatie mislukt: automatische live sync ontbreekt ({needle})')

print('[Machinepark] depannages, onderhoud en storingen verversen automatisch tussen toestellen')
