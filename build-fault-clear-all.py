from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
endpoint_path = ROOT / 'netlify/functions/fault-library.mjs'
frontend_path = ROOT / 'fault-library.js'

index = index_path.read_text(encoding='utf-8')
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

ACTION_MARKER = "if (action === 'clear-all-faults')"
if ACTION_MARKER not in endpoint:
    action_anchor = "    if (action === 'undo-last-import') {"
    action = r'''    if (action === 'clear-all-faults') {
      if (String(body?.confirm || '').trim().toUpperCase() !== 'VERWIJDER') {
        return json({ error: 'Bevestig het volledig verwijderen met VERWIJDER.' }, 400);
      }
      const removed = [...config.faults];
      if (!removed.length) {
        return json({ ok: true, faults: [], etag, canManage: true, removedCount: 0 });
      }
      const saved = await saveConfig(store, { version: 1, faults: [] }, etag, body?.etag || null);
      const savedConfig = normalizeConfig(saved.data);
      await writeClearAllFaultsAudit(store, access, removed);
      return json({
        ok: true,
        faults: savedConfig.faults,
        etag: saved.etag || null,
        canManage: true,
        removedCount: removed.length,
      });
    }

'''
    if endpoint.count(action_anchor) != 1:
        raise SystemExit('Storingen leegmaken: serveractie-anker niet uniek')
    endpoint = endpoint.replace(action_anchor, action + action_anchor, 1)

FRONT_MARKER = '// machinepark-fault-cache-reconnect-sync-v1'
if FRONT_MARKER not in frontend:
    old = "  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFaultFeature, { once: true });\n  else initFaultFeature();\n})();"
    new = "  // machinepark-fault-cache-reconnect-sync-v1\n  window.addEventListener('online', () => {\n    if (!canViewFaultLibrary()) return;\n    loadFaultLibrary(true).then(() => { if (state.view === 'faults') renderFaultLibrary(); }).catch(() => {});\n  });\n\n  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initFaultFeature, { once: true });\n  else initFaultFeature();\n})();"
    if frontend.count(old) != 1:
        raise SystemExit('Storingen leegmaken: frontend init-anker niet uniek')
    frontend = frontend.replace(old, new, 1)

BUTTON_MARKER = 'id="clearAllFaultsBtn"'
if BUTTON_MARKER not in index:
    anchor = '            <button class="btn danger" type="button" id="undoFaultExcelImportBtn">Laatste import ongedaan maken</button>\n'
    replacement = anchor + '            <button class="btn danger" type="button" id="clearAllFaultsBtn">Alle storingen verwijderen</button>\n'
    if index.count(anchor) != 1:
        raise SystemExit('Storingen leegmaken: Beheer-knoppenanker niet uniek')
    index = index.replace(anchor, replacement, 1)

UI_MARKER = 'data-machinepark-build-fix="fault-clear-all-admin-v1"'
if UI_MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="fault-clear-all-admin-v1">
(() => {
  async function clearAllFaultsFromAdmin() {
    const button = document.getElementById('clearAllFaultsBtn');
    if (!button) return;
    if (!confirm('Alle storingen verwijderen? Dit wist de volledige storingsbibliotheek voor alle gebruikers en synchroniseert daarna ook de lege lijst naar offline apparaten.')) return;
    const typed = prompt('Typ VERWIJDER om te bevestigen dat de volledige storingsbibliotheek mag worden leeggemaakt.');
    if (String(typed || '').trim().toUpperCase() !== 'VERWIJDER') {
      toast('Verwijderen geannuleerd');
      return;
    }

    const oldText = button.textContent;
    button.disabled = true;
    button.textContent = 'Storingen verwijderen…';
    try {
      const headers = await centralHeaders(true);
      const res = await fetch('/.netlify/functions/fault-library', {
        method: 'POST',
        cache: 'no-store',
        headers,
        body: JSON.stringify({ action: 'clear-all-faults', confirm: 'VERWIJDER' }),
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(data.error || text || `Storingen verwijderen mislukt (${res.status})`);

      if (typeof window.machineparkLoadFaultLibrary === 'function') await window.machineparkLoadFaultLibrary(true);
      if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
      const count = Number(data.removedCount || 0);
      toast(`Storingsbibliotheek leeggemaakt · ${count} storing${count === 1 ? '' : 'en'} verwijderd`);
    } catch (error) {
      console.error('Alle storingen verwijderen', error);
      alert('Storingsbibliotheek kon niet worden leeggemaakt: ' + (error?.message || 'onbekende fout'));
    } finally {
      button.disabled = false;
      button.textContent = oldText;
    }
  }

  function bindClearAllFaultsAdmin() {
    const button = document.getElementById('clearAllFaultsBtn');
    if (button) button.onclick = clearAllFaultsFromAdmin;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindClearAllFaultsAdmin, { once: true });
  else bindClearAllFaultsAdmin();
})();
</script>
'''
    anchor = '</body>'
    pos = index.rfind(anchor)
    if pos < 0:
        raise SystemExit('Storingen leegmaken: body-einde ontbreekt voor beheerknop')
    index = index[:pos] + script + '\n' + index[pos:]

index_path.write_text(index, encoding='utf-8')
endpoint_path.write_text(endpoint, encoding='utf-8')
frontend_path.write_text(frontend, encoding='utf-8')

for needle in [CONST, MARKER, '{ version: 1, faults: [] }', "remainingCount: 0", GET_MARKER, 'volledig leeggemaakt', ACTION_MARKER, "confirm || '').trim().toUpperCase() !== 'VERWIJDER'"]:
    if needle not in endpoint:
        raise SystemExit(f'Buildvalidatie mislukt: centrale leegmaaklogica ontbreekt ({needle})')
for needle in [FRONT_MARKER, "window.addEventListener('online'", 'loadFaultLibrary(true)', 'writeFaultCache']:
    if needle not in frontend:
        raise SystemExit(f'Buildvalidatie mislukt: offline storingscache-sync ontbreekt ({needle})')
for needle in [BUTTON_MARKER, UI_MARKER, 'Alle storingen verwijderen', "action: 'clear-all-faults'", "prompt('Typ VERWIJDER"]:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: Beheer-knop voor storingen ontbreekt ({needle})')

print('[Machinepark] Beheer heeft veilige knop om alle storingen centraal en offline te verwijderen')
