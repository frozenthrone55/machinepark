from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
endpoint_path = ROOT / 'netlify/functions/fault-library.mjs'

index = index_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')

MARKER = 'data-machinepark-build-fix="fault-import-undo-v1"'
BUTTON_MARKER = 'id="undoFaultExcelImportBtn"'

if BUTTON_MARKER not in index:
    anchor = '            <button class="btn" type="button" id="downloadFaultExcelTemplateBtn">Excel-sjabloon downloaden</button>\n'
    replacement = anchor + '            <button class="btn danger" type="button" id="undoFaultExcelImportBtn">Laatste import ongedaan maken</button>\n'
    if index.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: storings-Excel knoppenanker niet uniek')
    index = index.replace(anchor, replacement, 1)

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="fault-import-undo-v1">
(() => {
  async function undoFaultExcelImport() {
    const button = document.getElementById('undoFaultExcelImportBtn');
    if (!button) return;
    if (!confirm('Laatste storingsimport ongedaan maken? De storingsbibliotheek wordt teruggezet naar exact de toestand van vlak vóór die import. Dit kan alleen als er nadien geen andere storingswijzigingen zijn gebeurd.')) return;

    const oldText = button.textContent;
    button.disabled = true;
    button.textContent = 'Import terugdraaien…';
    try {
      const headers = await centralHeaders(true);
      const res = await fetch('/.netlify/functions/fault-library', {
        method: 'POST',
        cache: 'no-store',
        headers,
        body: JSON.stringify({ action: 'undo-last-import' }),
      });
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(data.error || text || `Terugdraaien mislukt (${res.status})`);

      if (typeof window.machineparkLoadFaultLibrary === 'function') await window.machineparkLoadFaultLibrary(true).catch(() => {});
      if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
      toast(`Storingsimport ongedaan gemaakt · ${data.restoredCount ?? 0} storing${Number(data.restoredCount) === 1 ? '' : 'en'} hersteld`);
    } catch (error) {
      console.error('Storingsimport ongedaan maken', error);
      alert('Import kon niet ongedaan worden gemaakt: ' + (error?.message || 'onbekende fout'));
    } finally {
      button.disabled = false;
      button.textContent = oldText;
    }
  }

  function bindFaultImportUndo() {
    const button = document.getElementById('undoFaultExcelImportBtn');
    if (button) button.onclick = undoFaultExcelImport;
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', bindFaultImportUndo, { once: true });
  else bindFaultImportUndo();
})();
</script>
'''
    anchor = '<script src="/offline-first.js"></script>'
    if index.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: offline runtime-anker niet uniek voor import-undo')
    index = index.replace(anchor, script + '\n' + anchor, 1)

UNDO_KEY_CONST = "const FAULT_IMPORT_UNDO_KEY = 'fault-import-undo-v1';"
if UNDO_KEY_CONST not in endpoint:
    anchor = "const MAX_FAULTS = 5000;\n"
    if endpoint.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: MAX_FAULTS-anker niet uniek')
    endpoint = endpoint.replace(anchor, anchor + UNDO_KEY_CONST + '\n', 1)

HELPER_MARKER = 'async function writeImportUndoAudit('
if HELPER_MARKER not in endpoint:
    helper_anchor = 'function faultImportKey(fault) {'
    helper = r'''
async function writeImportUndoAudit(store, auth, snapshot, restoredCount) {
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
      changeCount: Math.max(1, Number(snapshot?.added || 0) + Number(snapshot?.updated || 0)),
      changes: [{
        entityType: 'Storingen',
        entityId: 'excel-import-undo',
        entityLabel: 'Storingsbibliotheek Excel-import',
        action: 'import ongedaan gemaakt',
        fields: [
          { field: 'Oorspronkelijke import', before: snapshot?.importedAt || '—', after: 'ongedaan gemaakt' },
          { field: 'Nieuwe storingen in import', before: String(snapshot?.added || 0), after: 'teruggedraaid' },
          { field: 'Bijgewerkte storingen in import', before: String(snapshot?.updated || 0), after: 'teruggedraaid' },
          { field: 'Storingen na herstel', before: '—', after: String(restoredCount) },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('fault import undo audit', error);
  }
}

async function readFaultImportUndo(store) {
  return store.get(FAULT_IMPORT_UNDO_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
}

async function stageFaultImportUndo(store, config, etag, access) {
  const at = new Date().toISOString();
  const email = primaryEmailOf(access.user) || access.sub;
  const snapshot = {
    version: 1,
    status: 'pending',
    stagedAt: at,
    beforeEtag: etag || null,
    before: normalizeConfig(config),
    userId: access.sub,
    userEmail: email,
  };
  await store.setJSON(FAULT_IMPORT_UNDO_KEY, snapshot, { metadata: { type: 'fault-import-undo', status: 'pending', at } });
  return snapshot;
}

async function finalizeFaultImportUndo(store, staged, saved, added, updated, total) {
  const snapshot = {
    ...staged,
    status: 'ready',
    importedAt: new Date().toISOString(),
    afterEtag: saved?.etag || null,
    added,
    updated,
    total,
  };
  await store.setJSON(FAULT_IMPORT_UNDO_KEY, snapshot, { metadata: { type: 'fault-import-undo', status: 'ready', at: snapshot.importedAt } });
  return snapshot;
}

'''
    if endpoint.count(helper_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: faultImportKey-anker niet uniek')
    endpoint = endpoint.replace(helper_anchor, helper + helper_anchor, 1)

# Stage snapshot immediately before the atomic import write, then mark it ready only after success.
STAGE_MARKER = 'const stagedUndo = await stageFaultImportUndo(store, config, etag, access);'
if STAGE_MARKER not in endpoint:
    anchor = "      if (merged.length > MAX_FAULTS) return json({ error: `De storingsbibliotheek mag maximaal ${MAX_FAULTS} storingen bevatten.` }, 400);\n      const saved = await saveConfig(store, { version: 1, faults: merged }, etag, body?.etag || null);\n      await writeImportAudit(store, access, added, updated, incoming.length);"
    replacement = "      if (merged.length > MAX_FAULTS) return json({ error: `De storingsbibliotheek mag maximaal ${MAX_FAULTS} storingen bevatten.` }, 400);\n      const stagedUndo = await stageFaultImportUndo(store, config, etag, access);\n      const saved = await saveConfig(store, { version: 1, faults: merged }, etag, body?.etag || null);\n      await finalizeFaultImportUndo(store, stagedUndo, saved, added, updated, incoming.length);\n      await writeImportAudit(store, access, added, updated, incoming.length);"
    if endpoint.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: import-save-anker niet uniek')
    endpoint = endpoint.replace(anchor, replacement, 1)

ACTION_MARKER = "if (action === 'undo-last-import')"
if ACTION_MARKER not in endpoint:
    action_anchor = "    if (action === 'import-faults') {"
    action = r'''    if (action === 'undo-last-import') {
      const snapshot = await readFaultImportUndo(store);
      if (!snapshot || snapshot.status !== 'ready' || !snapshot.before || !Array.isArray(snapshot.before.faults)) {
        return json({ error: 'Er is geen terugdraaibare storingsimport beschikbaar. Imports van vóór deze functie hebben geen herstelmomentopname.' }, 409);
      }

      if (!snapshot.afterEtag || !etag || snapshot.afterEtag !== etag) {
        return json({ error: 'De storingsbibliotheek is na deze import nog gewijzigd. Terugdraaien is geblokkeerd zodat latere wijzigingen niet verloren gaan.' }, 409);
      }

      const restored = await saveConfig(store, snapshot.before, etag, etag);
      const restoredConfig = normalizeConfig(restored.data);
      const completed = {
        ...snapshot,
        status: 'undone',
        undoneAt: new Date().toISOString(),
        restoredEtag: restored.etag || null,
        restoredCount: restoredConfig.faults.length,
      };
      await store.setJSON(FAULT_IMPORT_UNDO_KEY, completed, { metadata: { type: 'fault-import-undo', status: 'undone', at: completed.undoneAt } });
      await writeImportUndoAudit(store, access, snapshot, restoredConfig.faults.length);
      return json({ ok: true, faults: restoredConfig.faults, etag: restored.etag || null, canManage: true, restoredCount: restoredConfig.faults.length });
    }

'''
    if endpoint.count(action_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: import-faults-anker niet uniek voor undo')
    endpoint = endpoint.replace(action_anchor, action + action_anchor, 1)

index_path.write_text(index, encoding='utf-8')
endpoint_path.write_text(endpoint, encoding='utf-8')

built_index = index_path.read_text(encoding='utf-8')
built_endpoint = endpoint_path.read_text(encoding='utf-8')
for needle in [BUTTON_MARKER, MARKER, 'Laatste import ongedaan maken', "action: 'undo-last-import'", 'Import terugdraaien…']:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: import-undo UI ontbreekt ({needle})')
for needle in [UNDO_KEY_CONST, HELPER_MARKER, ACTION_MARKER, STAGE_MARKER, 'afterEtag !== etag', "status: 'undone'", 'writeImportUndoAudit']:
    if needle not in built_endpoint:
        raise SystemExit(f'Buildvalidatie mislukt: import-undo serverlogica ontbreekt ({needle})')

print('[Machinepark] laatste storings-Excelimport veilig terugdraaibaar met servermomentopname')
