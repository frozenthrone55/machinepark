from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
text = path.read_text(encoding='utf-8')
MARKER = '// machinepark-sync-drift-recovery-v1'


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    text = text.replace(old, new, 1)


if MARKER not in text:
    replace_once(
        '  window.machineparkMergeOfflineSnapshots = mergeOfflineSnapshots;\n',
        '''  window.machineparkMergeOfflineSnapshots = mergeOfflineSnapshots;\n\n  // machinepark-sync-drift-recovery-v1\n  const LOCAL_WRITE_HINT_KEY = 'machinepark-local-write-pending-v1';\n\n  function sortedSyncStore(list) {\n    return [...(Array.isArray(list) ? list : [])].sort((a, b) => String(a?.id || '').localeCompare(String(b?.id || '')));\n  }\n\n  function snapshotStoresEqual(a, b) {\n    if (!a || !b) return false;\n    return stores.every((storeName) => sameValue(sortedSyncStore(a?.[storeName]), sortedSyncStore(b?.[storeName])));\n  }\n\n  function markPendingLocalWriteHint() {\n    try { localStorage.setItem(LOCAL_WRITE_HINT_KEY, new Date().toISOString()); } catch (_) {}\n  }\n\n  function hasPendingLocalWriteHint() {\n    try { return Boolean(localStorage.getItem(LOCAL_WRITE_HINT_KEY)); } catch (_) { return false; }\n  }\n\n  function clearPendingLocalWriteHint() {\n    try { localStorage.removeItem(LOCAL_WRITE_HINT_KEY); } catch (_) {}\n  }\n''',
        'drift helpers',
    )

    replace_once(
        "              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });\n              if (reconciledRemote || migratedPhotos) {",
        "              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });\n              clearPendingLocalWriteHint();\n              if (reconciledRemote || migratedPhotos) {",
        'pending hint wissen na push',
    )

    replace_once(
        '''      let meta = await readMeta();\n      if (meta.dirty || centralSync.offlineDirty) {\n        const pushed = await centralPush({ initial: true });''',
        '''      let meta = await readMeta();\n      const localBeforePull = await localSnapshot();\n      const localDrift = Boolean(meta.base) && !snapshotStoresEqual(meta.base, localBeforePull);\n      let pendingHint = hasPendingLocalWriteHint();\n\n      // Een lokale write kan op mobiel nog bestaan terwijl de asynchrone dirty-marker\n      // door slaapstand/tabwissel niet duurzaam werd weggeschreven. Vergelijk daarom\n      // ook de echte IndexedDB-inhoud met de laatst bevestigde centrale basis.\n      if (localDrift && !meta.dirty) {\n        centralSync.offlineDirty = true;\n        const marked = await writeMeta({\n          dirty: true,\n          etag: meta.etag || centralSync.etag || null,\n          base: meta.base || null,\n        });\n        meta = marked || { ...meta, dirty: true };\n      }\n      if (pendingHint && !localDrift && !meta.dirty && !centralSync.offlineDirty) {\n        clearPendingLocalWriteHint();\n        pendingHint = false;\n      }\n\n      if (meta.dirty || centralSync.offlineDirty || localDrift || pendingHint) {\n        const pushed = await centralPush({ initial: true });''',
        'driftcontrole voor pull',
    )

    replace_once(
        '''      centralSync.pending = true;\n      markDirty().catch(() => {});''',
        '''      centralSync.pending = true;\n      // Deze lokaleStorage-hint wordt synchroon gezet en overleeft het sneller sluiten\n      // of slapen van mobiele browsers. De IndexedDB dirty-marker blijft de hoofdbron.\n      markPendingLocalWriteHint();\n      markDirty().catch(() => {});''',
        'duurzame pending hint',
    )

    replace_once(
        '''    window.machineparkSyncOnlineNow = syncOnlineNow;\n\n    function scheduleImmediateOnlineSync() {''',
        '''    window.machineparkSyncOnlineNow = syncOnlineNow;\n\n    // Onderhoud en depannages zijn operationele registraties. Geef writes naar deze\n    // stores een korte, aparte sync-trigger zodat iOS/Android de 650ms algemene\n    // debounce niet hoeft af te wachten voordat de gebruiker de app verlaat.\n    let serviceWriteSyncTimer = null;\n    function queueServiceWriteSync(storeName) {\n      if (storeName !== 'maintenance' && storeName !== 'breakdowns') return;\n      markPendingLocalWriteHint();\n      clearTimeout(serviceWriteSyncTimer);\n      serviceWriteSyncTimer = setTimeout(async () => {\n        serviceWriteSyncTimer = null;\n        if (!navigator.onLine || !window.Clerk?.isSignedIn) return;\n        if (centralSync.pushTimer) {\n          clearTimeout(centralSync.pushTimer);\n          centralSync.pushTimer = null;\n        }\n        try {\n          setCentralSyncStatus('☁ Registratie centraal bevestigen…', 'busy');\n          await syncOnlineNow({ quiet: false });\n        } catch (error) {\n          console.warn('Directe service-synchronisatie', error);\n          if (isNetworkFailure(error)) setOfflineStatus();\n          else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');\n        }\n      }, 90);\n    }\n    window.machineparkQueueServiceWriteSync = queueServiceWriteSync;\n\n    const baseServicePut = typeof put === 'function' ? put : null;\n    if (baseServicePut) {\n      put = async function(storeName, item) {\n        const result = await baseServicePut(storeName, item);\n        queueServiceWriteSync(storeName);\n        return result;\n      };\n      window.put = put;\n    }\n\n    const baseServicePutMany = typeof putMany === 'function' ? putMany : null;\n    if (baseServicePutMany) {\n      putMany = async function(storeName, items) {\n        const result = await baseServicePutMany(storeName, items);\n        queueServiceWriteSync(storeName);\n        return result;\n      };\n      window.putMany = putMany;\n    }\n\n    const baseDeleteServiceRecordAtomic = typeof deleteServiceRecordAtomic === 'function' ? deleteServiceRecordAtomic : null;\n    if (baseDeleteServiceRecordAtomic) {\n      deleteServiceRecordAtomic = async function(storeName, record) {\n        const result = await baseDeleteServiceRecordAtomic(storeName, record);\n        queueServiceWriteSync(storeName);\n        return result;\n      };\n      window.deleteServiceRecordAtomic = deleteServiceRecordAtomic;\n    }\n\n    function scheduleImmediateOnlineSync() {''',
        'snelle service sync',
    )

path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
required = [
    MARKER,
    'machinepark-local-write-pending-v1',
    'function snapshotStoresEqual(a, b)',
    'Boolean(meta.base) && !snapshotStoresEqual(meta.base, localBeforePull)',
    'markPendingLocalWriteHint();',
    'clearPendingLocalWriteHint();',
    "storeName !== 'maintenance' && storeName !== 'breakdowns'",
    'queueServiceWriteSync(storeName)',
    'window.machineparkQueueServiceWriteSync = queueServiceWriteSync;',
    "setCentralSyncStatus('☁ Registratie centraal bevestigen…', 'busy')",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: drift-herstel ontbreekt ({needle})')

print('[Machinepark] lokale service-drift wordt herkend en mobiele writes worden snel centraal bevestigd')
