from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
text = path.read_text(encoding='utf-8')

MARKER = '// machinepark-online-sync-consistency-v1'

if MARKER not in text:
    # 1. Als een 409 tot een echte remote/local merge leidt, moet die samengevoegde
    # toestand na de geslaagde PUT ook lokaal worden toegepast. Anders is de server
    # correct terwijl de geopende UI tot een volgende pull verouderd blijft.
    old = "          let conflicts = 0;\n\n          for (let attempt = 0; attempt < 3; attempt += 1) {"
    new = "          let conflicts = 0;\n          let reconciledRemote = false;\n\n          for (let attempt = 0; attempt < 3; attempt += 1) {"
    if text.count(old) != 1:
        raise SystemExit('Online sync: conflicts-anker niet uniek')
    text = text.replace(old, new, 1)

    old = "            const merged = mergeOfflineSnapshots(meta.base, local, remote.data);\n            local = merged.data;\n            conflicts += merged.conflicts;"
    new = "            const merged = mergeOfflineSnapshots(meta.base, local, remote.data);\n            local = merged.data;\n            reconciledRemote = true;\n            conflicts += merged.conflicts;"
    if text.count(old) != 1:
        raise SystemExit('Online sync: merge-anker niet uniek')
    text = text.replace(old, new, 1)

    old = "              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });\n              if (migratedPhotos) await refresh();\n              setCentralSyncStatus(conflicts ? `☁ Gesynchroniseerd · ${conflicts} conflict(en) lokaal behouden` : '☁ Alles centraal opgeslagen', 'ok');"
    new = "              await writeMeta({ etag: centralSync.etag || null, base: local, dirty: false });\n              if (reconciledRemote || migratedPhotos) {\n                await replaceLocalSnapshot(local);\n                if (window.__koffieServiceStarted && document.getElementById('view-dashboard')) await refresh();\n              }\n              setCentralSyncStatus(conflicts ? `☁ Gesynchroniseerd · ${conflicts} conflict(en) lokaal behouden` : '☁ Alles centraal opgeslagen', 'ok');"
    if text.count(old) != 1:
        raise SystemExit('Online sync: push-success-anker niet uniek')
    text = text.replace(old, new, 1)

    # 2. Aparte centrale bronnen (werkbonnen en storingen) horen bij dezelfde online
    # waarheid. Forceer ze bij online synchronisatie; een reeds gevulde JS-array mag
    # geen reden zijn om een nieuwere serverversie over te slaan.
    old = "    function primeOfflineExtras() {\n      if (!navigator.onLine) return;\n      if (typeof window.machineparkLoadWorkOrderTemplates === 'function') {\n        setTimeout(() => window.machineparkLoadWorkOrderTemplates().catch(() => {}), 1000);\n      }\n    }"
    new = "    async function refreshOnlineExtras() {\n      if (!navigator.onLine || !window.Clerk?.isSignedIn) return;\n      const tasks = [];\n      if (typeof window.machineparkLoadWorkOrderTemplates === 'function') {\n        tasks.push(window.machineparkLoadWorkOrderTemplates(true));\n      }\n      if (typeof window.machineparkLoadFaultLibrary === 'function') {\n        tasks.push(window.machineparkLoadFaultLibrary(true).then(() => {\n          if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();\n        }));\n      }\n      if (tasks.length) await Promise.allSettled(tasks);\n    }\n    window.machineparkRefreshOnlineExtras = refreshOnlineExtras;\n\n    function primeOfflineExtras() {\n      if (!navigator.onLine) return;\n      refreshOnlineExtras().catch((error) => console.warn('Extra centrale gegevens verversen', error));\n    }"
    if text.count(old) != 1:
        raise SystemExit('Online sync: extras-anker niet uniek')
    text = text.replace(old, new, 1)

    # 3. Bij opstart met offline wijzigingen na de push altijd nog een bevestigende
    # pull uitvoeren. Dit garandeert dat deze client dezelfde serverwaarheid toont.
    old = "          await centralPush({ initial: true });\n          primeOfflineExtras();\n          return;"
    new = "          const pushed = await centralPush({ initial: true });\n          if (!pushed?.offline) await centralPull({ apply: true, quiet: true });\n          await refreshOnlineExtras();\n          return;"
    if text.count(old) != 1:
        raise SystemExit('Online sync: dirty-startup-anker niet uniek')
    text = text.replace(old, new, 1)

    # 4. Alleen offline gaan is géén gegevenswijziging. Echte writes roepen reeds
    # scheduleCentralSync/markDirty aan. Dit voorkomt een onnodige push van een oude
    # snapshot zodra de verbinding terugkomt.
    old = "    window.addEventListener('offline', () => {\n      markDirty().catch(() => {});\n      setOfflineStatus();"
    new = "    window.addEventListener('offline', () => {\n      setOfflineStatus();"
    if text.count(old) != 1:
        raise SystemExit('Online sync: offline-event-anker niet uniek')
    text = text.replace(old, new, 1)

    # 5. Eén geserialiseerde app-brede online sync voor reconnect, focus en tab-terugkeer.
    # Daardoor hoeft de gebruiker niet te wachten op de 20s poll of tweemaal te refreshen.
    old = "    window.addEventListener('online', async () => {\n      setCentralSyncStatus('☁ Verbinding hersteld · synchroniseren…', 'busy');\n      if (document.documentElement.classList.contains('machinepark-offline-session') && !window.Clerk?.isSignedIn) {\n        location.reload();\n        return;\n      }\n      if (!window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return;\n      try {\n        const meta = await readMeta();\n        if (meta.dirty || centralSync.offlineDirty) await centralPush({ initial: true });\n        await centralPull({ apply: true, quiet: true });\n        setCentralSyncStatus('☁ Alles centraal gesynchroniseerd', 'ok');\n        if (typeof toast === 'function') toast('Verbinding hersteld · offline wijzigingen zijn gesynchroniseerd.');\n        primeOfflineExtras();\n      } catch (error) {\n        console.warn('Automatische reconnect-sync', error);\n        if (isNetworkFailure(error)) setOfflineStatus();\n        else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');\n      }\n    });"
    new = "    // machinepark-online-sync-consistency-v1\n    let immediateOnlineSyncPromise = null;\n    let immediateOnlineSyncTimer = null;\n\n    async function syncOnlineNow({ quiet = true } = {}) {\n      if (!navigator.onLine || !window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return { offline: !navigator.onLine };\n      if (immediateOnlineSyncPromise) return immediateOnlineSyncPromise;\n      immediateOnlineSyncPromise = (async () => {\n        const meta = await readMeta();\n        if (meta.dirty || centralSync.offlineDirty) {\n          const pushed = await centralPush({ initial: true });\n          if (pushed?.offline) return pushed;\n        }\n        const pulled = await centralPull({ apply: true, quiet: true });\n        await refreshOnlineExtras();\n        if (!quiet) setCentralSyncStatus('☁ Alles centraal gesynchroniseerd', 'ok');\n        return pulled;\n      })();\n      try { return await immediateOnlineSyncPromise; }\n      finally { immediateOnlineSyncPromise = null; }\n    }\n    window.machineparkSyncOnlineNow = syncOnlineNow;\n\n    function scheduleImmediateOnlineSync() {\n      if (!navigator.onLine || !window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return;\n      clearTimeout(immediateOnlineSyncTimer);\n      immediateOnlineSyncTimer = setTimeout(() => {\n        immediateOnlineSyncTimer = null;\n        syncOnlineNow({ quiet: true }).catch((error) => {\n          console.warn('Directe online synchronisatie', error);\n          if (isNetworkFailure(error)) setOfflineStatus();\n          else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');\n        });\n      }, 120);\n    }\n\n    window.addEventListener('online', async () => {\n      setCentralSyncStatus('☁ Verbinding hersteld · synchroniseren…', 'busy');\n      if (document.documentElement.classList.contains('machinepark-offline-session') && !window.Clerk?.isSignedIn) {\n        location.reload();\n        return;\n      }\n      if (!window.__koffieServiceStarted || !window.Clerk?.isSignedIn) return;\n      try {\n        await syncOnlineNow({ quiet: false });\n        if (typeof toast === 'function') toast('Verbinding hersteld · alles is centraal gesynchroniseerd.');\n      } catch (error) {\n        console.warn('Automatische reconnect-sync', error);\n        if (isNetworkFailure(error)) setOfflineStatus();\n        else setCentralSyncStatus('☁ Synchronisatie wacht op controle', 'error');\n      }\n    });\n\n    window.addEventListener('focus', scheduleImmediateOnlineSync);\n    document.addEventListener('visibilitychange', () => {\n      if (document.visibilityState === 'visible') scheduleImmediateOnlineSync();\n    });"
    if text.count(old) != 1:
        raise SystemExit('Online sync: reconnect-anker niet uniek')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')

built = path.read_text(encoding='utf-8')
required = [
    MARKER,
    'let reconciledRemote = false;',
    'reconciledRemote = true;',
    'await replaceLocalSnapshot(local);',
    'async function refreshOnlineExtras()',
    'machineparkLoadWorkOrderTemplates(true)',
    'machineparkLoadFaultLibrary(true)',
    'async function syncOnlineNow',
    'window.machineparkSyncOnlineNow = syncOnlineNow;',
    "window.addEventListener('focus', scheduleImmediateOnlineSync);",
    "document.addEventListener('visibilitychange'",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: app-brede online sync ontbreekt ({needle})')

# Alleen de offline-eventhandler mag niet meer blind dirty markeren.
offline_anchor = built.index("window.addEventListener('offline'")
offline_end = built.index("window.addEventListener('online'", offline_anchor)
offline_section = built[offline_anchor:offline_end]
if 'markDirty().catch' in offline_section:
    raise SystemExit('Buildvalidatie mislukt: offline gaan markeert nog steeds onterecht de dataset dirty')

print('[Machinepark] volledige app synchroniseert bij online opstart, reconnect, focus en merge direct met centrale waarheid')
