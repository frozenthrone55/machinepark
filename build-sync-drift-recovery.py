from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
text = path.read_text(encoding='utf-8')
MARKER = '// machinepark-sync-drift-recovery-v1'
RACE_MARKER = '// machinepark-new-entry-race-v1'


def replace_once(old, new, label):
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    text = text.replace(old, new, 1)


if MARKER not in text:
    replace_once(
        '  window.machineparkMergeOfflineSnapshots = mergeOfflineSnapshots;\n',
        '''  window.machineparkMergeOfflineSnapshots = mergeOfflineSnapshots;\n\n  // machinepark-sync-drift-recovery-v1\n  // machinepark-new-entry-race-v1\n  const LOCAL_WRITE_HINT_KEY = 'machinepark-local-write-pending-v1';\n  let localWriteSequenceValue = 0;\n\n  function localWriteSequence() {\n    return localWriteSequenceValue;\n  }\n\n  function noteLocalWrite() {\n    localWriteSequenceValue += 1;\n    return localWriteSequenceValue;\n  }\n\n  function sortedSyncStore(list) {\n    return [...(Array.isArray(list) ? list : [])].sort((a, b) => String(a?.id || '').localeCompare(String(b?.id || '')));\n  }\n\n  function snapshotStoresEqual(a, b) {\n    if (!a || !b) return false;\n    return stores.every((storeName) => sameValue(sortedSyncStore(a?.[storeName]), sortedSyncStore(b?.[storeName])));\n  }\n\n  function markPendingLocalWriteHint() {\n    try { localStorage.setItem(LOCAL_WRITE_HINT_KEY, new Date().toISOString()); } catch (_) {}\n  }\n\n  function hasPendingLocalWriteHint() {\n    try { return Boolean(localStorage.getItem(LOCAL_WRITE_HINT_KEY)); } catch (_) { return false; }\n  }\n\n  function clearPendingLocalWriteHint() {\n    try { localStorage.removeItem(LOCAL_WRITE_HINT_KEY); } catch (_) {}\n  }\n''',
        'drift helpers',
    )

    # Een push kan al bezig zijn wanneer de gebruiker een volgende invoer opslaat.
    # Onthoud daarom welke lokale versie de push werkelijk bevatte. Alleen die versie
    # mag na serverbevestiging als schoon worden gemarkeerd.
    replace_once(
        '''          const migratedPhotos = await flushOfflinePhotos();\n          let local = await localSnapshot();\n          let meta = await readMeta();''',
        '''          const migratedPhotos = await flushOfflinePhotos();\n          const pushWriteSequence = localWriteSequence();\n          let local = await localSnapshot();\n          const pushStartedLocal = local;\n          let meta = await readMeta();''',
        'push lokale beginsnapshot',
    )

    replace_once(
        '''              centralSync.etag = result.body?.etag || expectedEtag || centralSync.etag;\n              centralSync.lastRemoteAt = local.updatedAt || '';\n              centralSync.offlineDirty = false;\n              centralSync.pending = false;\n              window.machineparkLastSyncError = null;\n              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });\n              if (reconciledRemote || migratedPhotos) {\n                await replaceLocalSnapshot(local);\n                if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();\n              }\n              setCentralSyncStatus(conflicts ? `☁ Gesynchroniseerd · ${conflicts} conflict(en) veilig samengevoegd` : '☁ Alles centraal opgeslagen', 'ok');\n              return { ok: true, conflicts };''',
        '''              const confirmedEtag = result.body?.etag || expectedEtag || centralSync.etag;\n              centralSync.etag = confirmedEtag;\n              centralSync.lastRemoteAt = local.updatedAt || '';\n              window.machineparkLastSyncError = null;\n\n              // Lees na de netwerk-PUT nogmaals de echte IndexedDB. Een invoer die\n              // tijdens de PUT werd opgeslagen mag niet als onderdeel van deze oudere\n              // push worden beschouwd en mag zeker niet door een merge worden overschreven.\n              const localAfterPush = await localSnapshot();\n              const newerLocalWrite = localWriteSequence() !== pushWriteSequence\n                || !snapshotStoresEqual(pushStartedLocal, localAfterPush);\n\n              if (newerLocalWrite) {\n                centralSync.offlineDirty = true;\n                centralSync.pending = true;\n                markPendingLocalWriteHint();\n\n                // Na een 409-merge bewaren we bewust de vorige ETag/basis. De volgende\n                // push krijgt dan opnieuw een 409 en kan de zojuist gemaakte invoer\n                // veilig met de reeds bevestigde servermerge samenvoegen.\n                const retryEtag = reconciledRemote ? (expectedEtag || meta.etag || null) : (confirmedEtag || null);\n                const retryBase = reconciledRemote ? pushStartedLocal : local;\n                await writeMeta({ etag: retryEtag, base: retryBase, dirty: true });\n                setCentralSyncStatus('☁ Nieuwe invoer lokaal bewaard · synchronisatie volgt…', 'busy');\n                return { ok: true, conflicts, pending: true };\n              }\n\n              if (reconciledRemote || migratedPhotos) {\n                await replaceLocalSnapshot(local);\n                if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();\n              }\n\n              await writeMeta({ etag: confirmedEtag || null, base: local, dirty: false });\n\n              // Ook tijdens de asynchrone meta-write kan nog een nieuwe lokale write\n              // binnenkomen. Controleer de teller daarom een laatste keer vóór we de\n              // dataset als volledig gesynchroniseerd markeren.\n              if (localWriteSequence() !== pushWriteSequence) {\n                centralSync.offlineDirty = true;\n                centralSync.pending = true;\n                markPendingLocalWriteHint();\n                await writeMeta({ etag: confirmedEtag || null, base: local, dirty: true });\n                setCentralSyncStatus('☁ Nieuwe invoer lokaal bewaard · synchronisatie volgt…', 'busy');\n                return { ok: true, conflicts, pending: true };\n              }\n\n              centralSync.offlineDirty = false;\n              centralSync.pending = false;\n              clearPendingLocalWriteHint();\n              setCentralSyncStatus(conflicts ? `☁ Gesynchroniseerd · ${conflicts} conflict(en) veilig samengevoegd` : '☁ Alles centraal opgeslagen', 'ok');\n              return { ok: true, conflicts };''',
        'push-success racebeveiliging',
    )

    replace_once(
        '''      let meta = await readMeta();\n      if (meta.dirty || centralSync.offlineDirty) {\n        const pushed = await centralPush({ initial: true });''',
        '''      let meta = await readMeta();\n      const localBeforePull = await localSnapshot();\n      const localDrift = Boolean(meta.base) && !snapshotStoresEqual(meta.base, localBeforePull);\n      let pendingHint = hasPendingLocalWriteHint();\n\n      // Een lokale write kan op mobiel nog bestaan terwijl de asynchrone dirty-marker\n      // door slaapstand/tabwissel niet duurzaam werd weggeschreven. Vergelijk daarom\n      // ook de echte IndexedDB-inhoud met de laatst bevestigde centrale basis.\n      if (localDrift && !meta.dirty) {\n        centralSync.offlineDirty = true;\n        const marked = await writeMeta({\n          dirty: true,\n          etag: meta.etag || centralSync.etag || null,\n          base: meta.base || null,\n        });\n        meta = marked || { ...meta, dirty: true };\n      }\n      if (pendingHint && !localDrift && !meta.dirty && !centralSync.offlineDirty) {\n        clearPendingLocalWriteHint();\n        pendingHint = false;\n      }\n\n      if (meta.dirty || centralSync.offlineDirty || localDrift || pendingHint) {\n        const pushed = await centralPush({ initial: true });''',
        'driftcontrole voor pull',
    )

    # Leg vlak vóór de GET vast welke lokale gegevens werkelijk aanwezig zijn. Een
    # IndexedDB getAll wacht vanzelf op reeds lopende write-transacties. Daardoor ziet
    # de tweede snapshot hieronder ook serviceverslagen die rechtstreeks via een eigen
    # transactie worden opgeslagen en niet alleen writes via put()/putMany().
    replace_once(
        '''        meta = await readMeta();\n        if (meta.dirty) return { exists: false, pending: true };\n      }\n\n      const headers = await centralHeaders(false);''',
        '''        meta = await readMeta();\n        if (meta.dirty) return { exists: false, pending: true };\n      }\n\n      const pullWriteSequence = localWriteSequence();\n      const pullLocalBaseline = await localSnapshot();\n      const headers = await centralHeaders(false);''',
        'pull beginsnapshot',
    )

    replace_once(
        '''      if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);\n\n      if (!body.exists) {''',
        '''      if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);\n\n      // CRUCIAAL: de GET kan gestart zijn vóór de gebruiker op Opslaan drukte. Lees\n      // vlak vóór het toepassen nogmaals IndexedDB. Is er intussen ook maar één store\n      // veranderd, dan mag deze oudere serverkopie de lokale invoer niet vervangen.\n      const localBeforeApply = await localSnapshot();\n      const localChangedDuringPull = localWriteSequence() !== pullWriteSequence\n        || !snapshotStoresEqual(pullLocalBaseline, localBeforeApply)\n        || centralSync.pending\n        || centralSync.offlineDirty\n        || hasPendingLocalWriteHint();\n\n      if (localChangedDuringPull) {\n        centralSync.offlineDirty = true;\n        centralSync.pending = true;\n        markPendingLocalWriteHint();\n        await writeMeta({\n          dirty: true,\n          etag: meta.etag || centralSync.etag || null,\n          base: meta.base || null,\n        });\n        setCentralSyncStatus('☁ Nieuwe invoer lokaal bewaard · synchronisatie volgt…', 'busy');\n        return {\n          exists: Boolean(body.exists),\n          pending: true,\n          skippedApply: true,\n          etag: body.etag || centralSync.etag || null,\n        };\n      }\n\n      if (!body.exists) {''',
        'pull toepassen racebeveiliging',
    )

    replace_once(
        '''      centralSync.pending = true;\n      markDirty().catch(() => {});''',
        '''      noteLocalWrite();\n      centralSync.pending = true;\n      // Deze lokaleStorage-hint wordt synchroon gezet en overleeft het sneller sluiten\n      // of slapen van mobiele browsers. De IndexedDB dirty-marker blijft de hoofdbron.\n      markPendingLocalWriteHint();\n      markDirty().catch(() => {});''',
        'duurzame pending hint en write-teller',
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
    RACE_MARKER,
    'machinepark-local-write-pending-v1',
    'function localWriteSequence()',
    'function noteLocalWrite()',
    'function snapshotStoresEqual(a, b)',
    'Boolean(meta.base) && !snapshotStoresEqual(meta.base, localBeforePull)',
    'const pushWriteSequence = localWriteSequence();',
    'const pushStartedLocal = local;',
    'const localAfterPush = await localSnapshot();',
    'const newerLocalWrite = localWriteSequence() !== pushWriteSequence',
    'const pullLocalBaseline = await localSnapshot();',
    'const localBeforeApply = await localSnapshot();',
    '!snapshotStoresEqual(pullLocalBaseline, localBeforeApply)',
    'skippedApply: true',
    "setCentralSyncStatus('☁ Nieuwe invoer lokaal bewaard · synchronisatie volgt…', 'busy')",
    'markPendingLocalWriteHint();',
    'clearPendingLocalWriteHint();',
    "storeName !== 'maintenance' && storeName !== 'breakdowns'",
    'queueServiceWriteSync(storeName)',
    'window.machineparkQueueServiceWriteSync = queueServiceWriteSync;',
    "setCentralSyncStatus('☁ Registratie centraal bevestigen…', 'busy')",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: drift/race-herstel ontbreekt ({needle})')

print('[Machinepark] nieuwe invoer kan niet meer door een reeds lopende pull/push worden overschreven')
