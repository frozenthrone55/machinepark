from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
offline_path = ROOT / 'offline-first.js'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="auto-live-sync-v1"'
DEVICE_SYNC_MARKER = '// machinepark-device-write-fast-sync-v1'
CORE_SYNC_MARKER = '// machinepark-core-store-fast-sync-v1'

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
      if (typeof window.machineparkLoadManualLibrary === 'function') {
        await window.machineparkLoadManualLibrary(true);
        if (typeof window.machineparkRenderManualLibrary === 'function') {
          window.machineparkRenderManualLibrary();
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

# Alle centrale stores bevatten wijzigingen die na één opslag onmiddellijk betrouwbaar
# op de server moeten staan. Onderhoud en depannages hadden deze route al; toestellen,
# onderdelen en acties krijgen dezelfde snelle bevestiging. Daardoor kan een live pull
# geen oudere centrale kopie terugzetten tussen de eerste lokale opslag en de normale
# 650ms debounce.
offline = offline_path.read_text(encoding='utf-8')
if CORE_SYNC_MARKER not in offline:
    old = """    function queueServiceWriteSync(storeName) {
      if (storeName !== 'maintenance' && storeName !== 'breakdowns') return;
      markPendingLocalWriteHint();"""
    new = """    function queueServiceWriteSync(storeName) {
      // machinepark-device-write-fast-sync-v1
      // machinepark-core-store-fast-sync-v1
      if (storeName !== 'maintenance' && storeName !== 'breakdowns' && storeName !== 'devices' && storeName !== 'parts' && storeName !== 'actions') return;
      markPendingLocalWriteHint();"""
    if offline.count(old) != 1:
        raise SystemExit('Buildvalidatie mislukt: snelle write-sync voor centrale stores niet uniek gevonden')
    offline = offline.replace(old, new, 1)
    offline_path.write_text(offline, encoding='utf-8')

required = [
    MARKER,
    'LIVE_SYNC_INTERVAL_MS = 3000',
    'window.machineparkSyncOnlineNow({ quiet: true })',
    'window.machineparkLoadFaultLibrary(true)',
    'window.machineparkRenderFaultLibrary()',
    'window.machineparkLoadManualLibrary(true)',
    'window.machineparkRenderManualLibrary()',
    "window.addEventListener('online'",
    "window.addEventListener('focus'",
    "document.addEventListener('visibilitychange'",
    "rfind('</body>')",
]
for needle in required:
    if needle not in index and needle != "rfind('</body>')":
        raise SystemExit(f'Buildvalidatie mislukt: automatische live sync ontbreekt ({needle})')

built_offline = offline_path.read_text(encoding='utf-8')
for needle in [
    DEVICE_SYNC_MARKER,
    CORE_SYNC_MARKER,
    "storeName !== 'maintenance' && storeName !== 'breakdowns' && storeName !== 'devices' && storeName !== 'parts' && storeName !== 'actions'",
    'queueServiceWriteSync(storeName)',
]:
    if needle not in built_offline:
        raise SystemExit(f'Buildvalidatie mislukt: snelle centrale store-sync ontbreekt ({needle})')

print('[Machinepark] onderdelen, toestellen, onderhoud, depannages en acties krijgen snelle centrale write-bevestiging')
