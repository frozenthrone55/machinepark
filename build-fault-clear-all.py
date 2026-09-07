from pathlib import Path

ROOT = Path(__file__).resolve().parent
endpoint_path = ROOT / 'netlify/functions/fault-library.mjs'
frontend_path = ROOT / 'fault-library.js'

endpoint = endpoint_path.read_text(encoding='utf-8')
frontend = frontend_path.read_text(encoding='utf-8')

CONST = "const FAULT_CLEAR_ALL_KEY = 'migration/fault-clear-all-v1';"
if CONST not in endpoint:
    anchor = "const FAULT_KEEP_ONLY_WATERSELECTOR_KEY = 'migration/fault-keep-only-00005-waterselector-bravilor-bolero-v1';\n"
    if endpoint.count(anchor) != 1:
        raise SystemExit('Storingen leegmaken: const-anker niet uniek')
    endpoint = endpoint.replace(anchor, anchor + CONST + '\n', 1)

MARKER = 'async function applyOneTimeClearAllFaults('
if MARKER not in endpoint:
    anchor = '\nexport default async (req) => {'
    helper = r'''

async function writeClearAllFaultsAudit(store, auth, removed) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: Math.max(1, removed.length),
      changes: [{
        entityType: 'Storingen',
        entityId: 'fault-library-clear-all',
        entityLabel: 'Storingsbibliotheek',
        action: 'volledig leeggemaakt',
        fields: [
          { field: 'Storingen', before: String(removed.length), after: '0' },
          { field: 'Offline cache', before: 'oude bibliotheek mogelijk aanwezig', after: 'wordt bij online synchronisatie vervangen door lege lijst' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('clear all faults audit', error);
  }
}

async function applyOneTimeClearAllFaults(store, access, entry, config) {
  if (!canManage(access)) return { entry, config, cleanup: null };
  const migration = await store.get(FAULT_CLEAR_ALL_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
  if (migration?.done) return { entry, config, cleanup: migration };

  const removed = [...config.faults];
  let nextEntry = entry;
  let nextConfig = config;

  if (removed.length) {
    nextEntry = await saveConfig(
      store,
      { version: 1, faults: [] },
      entry?.etag || null,
      entry?.etag || null,
    );
    nextConfig = normalizeConfig(nextEntry.data);
  }

  await writeClearAllFaultsAudit(store, access, removed);
  const cleanup = {
    done: true,
    at: new Date().toISOString(),
    removedCount: removed.length,
    remainingCount: 0,
  };
  await store.setJSON(FAULT_CLEAR_ALL_KEY, cleanup, { metadata: { type: 'one-time-migration' } });
  return { entry: nextEntry, config: nextConfig, cleanup };
}
'''
    if endpoint.count(anchor) != 1:
        raise SystemExit('Storingen leegmaken: export-anker niet uniek')
    endpoint = endpoint.replace(anchor, helper + anchor, 1)

GET_MARKER = 'clearAllFaultsCleanup: clearedAll.cleanup'
if GET_MARKER not in endpoint:
    old = "      const cleanedGlobal = await applyOneTimeKeepOnlyWaterselectorCleanup(store, access, entry, config);\n      entry = cleanedGlobal.entry;\n      config = cleanedGlobal.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup, keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup }, 200, etag ? { etag } : {});"
    new = "      const cleanedGlobal = await applyOneTimeKeepOnlyWaterselectorCleanup(store, access, entry, config);\n      entry = cleanedGlobal.entry;\n      config = cleanedGlobal.config;\n      const clearedAll = await applyOneTimeClearAllFaults(store, access, entry, config);\n      entry = clearedAll.entry;\n      config = clearedAll.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup, keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup, clearAllFaultsCleanup: clearedAll.cleanup }, 200, etag ? { etag } : {});"
    if endpoint.count(old) != 1:
        raise SystemExit('Storingen leegmaken: GET-anker niet uniek')
    endpoint = endpoint.replace(old, new, 1)

FRONT_MARKER = '// machinepark-fault-cache-reconnect-sync-v1'
if FRONT_MARKER not in frontend:
    old = "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFaultFeature, { once: true });\n  else initFaultFeature();\n})();"
    new = "  // machinepark-fault-cache-reconnect-sync-v1\n  window.addEventListener('online', () => {\n    if (!canViewFaultLibrary()) return;\n    loadFaultLibrary(true).then(() => { if (state.view === 'faults') renderFaultLibrary(); }).catch(() => {});\n  });\n\n  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFaultFeature, { once: true });\n  else initFaultFeature();\n})();"
    if frontend.count(old) != 1:
        raise SystemExit('Storingen leegmaken: frontend init-anker niet uniek')
    frontend = frontend.replace(old, new, 1)

endpoint_path.write_text(endpoint, encoding='utf-8')
frontend_path.write_text(frontend, encoding='utf-8')

for needle in [CONST, MARKER, '{ version: 1, faults: [] }', "remainingCount: 0", GET_MARKER, 'volledig leeggemaakt']:
    if needle not in endpoint:
        raise SystemExit(f'Buildvalidatie mislukt: centrale leegmaaklogica ontbreekt ({needle})')
for needle in [FRONT_MARKER, "window.addEventListener('online'", 'loadFaultLibrary(true)', 'writeFaultCache']:
    if needle not in frontend:
        raise SystemExit(f'Buildvalidatie mislukt: offline storingscache-sync ontbreekt ({needle})')

print('[Machinepark] storingsbibliotheek wordt eenmalig volledig leeggemaakt en offline cache synchroniseert bij reconnect')
