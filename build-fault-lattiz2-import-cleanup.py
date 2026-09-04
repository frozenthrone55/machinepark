from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'netlify/functions/fault-library.mjs'
text = path.read_text(encoding='utf-8')

CONST = "const LATTIZ2_IMPORT_CLEANUP_KEY = 'migration/fault-lattiz2-import-cleanup-v1';"
if CONST not in text:
    anchor = "const LATTIZ_CLEANUP_KEY = 'migration/fault-lattiz-cleanup-keep-00005-v1';\n"
    if text.count(anchor) != 1:
        raise SystemExit('Lattiz cleanup const-anker niet uniek')
    text = text.replace(anchor, anchor + CONST + '\n', 1)

MARKER = 'async function applyOneTimeLattiz2ImportCleanup('
if MARKER not in text:
    anchor = '\nexport default async (req) => {'
    helper = r'''

function isLattiz2ImportedFault(fault) {
  return cleanupNorm(fault?.brand) === 'lattiz2' || cleanupNorm(fault?.model) === 'lattiz2';
}

async function writeLattiz2ImportCleanupAudit(store, auth, removed) {
  if (!removed.length) return;
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id, at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: removed.length,
      changes: [{
        entityType: 'Storingen',
        entityId: 'lattiz2-import-cleanup',
        entityLabel: 'Foutieve Lattiz2 Excel-import',
        action: 'import volledig verwijderd',
        fields: [
          { field: 'Toepassing', before: 'lattiz2 · alle modellen', after: 'verwijderd' },
          { field: 'Verwijderde storingen', before: String(removed.length), after: '0' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('Lattiz2 import cleanup audit', error);
  }
}

async function applyOneTimeLattiz2ImportCleanup(store, access, entry, config) {
  if (!canManage(access)) return { entry, config, cleanup: null };
  const migration = await store.get(LATTIZ2_IMPORT_CLEANUP_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
  if (migration?.done) return { entry, config, cleanup: migration };

  const removed = config.faults.filter(isLattiz2ImportedFault);
  let nextEntry = entry;
  let nextConfig = config;
  if (removed.length) {
    nextEntry = await saveConfig(
      store,
      { version: 1, faults: config.faults.filter((fault) => !isLattiz2ImportedFault(fault)) },
      entry?.etag || null,
      entry?.etag || null,
    );
    nextConfig = normalizeConfig(nextEntry.data);
    await writeLattiz2ImportCleanupAudit(store, access, removed);
  }
  const cleanup = { done: true, at: new Date().toISOString(), removedCount: removed.length };
  await store.setJSON(LATTIZ2_IMPORT_CLEANUP_KEY, cleanup, { metadata: { type: 'one-time-migration' } });
  return { entry: nextEntry, config: nextConfig, cleanup };
}
'''
    if text.count(anchor) != 1:
        raise SystemExit('export-anker niet uniek')
    text = text.replace(anchor, helper + anchor, 1)

GET_MARKER = 'lattiz2Cleanup: cleanedLattiz2.cleanup'
if GET_MARKER not in text:
    old = "      const migrated = await applyOneTimeLattizCleanup(store, access, entry, config);\n      entry = migrated.entry;\n      config = migrated.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup }, 200, etag ? { etag } : {});"
    new = "      const migrated = await applyOneTimeLattizCleanup(store, access, entry, config);\n      entry = migrated.entry;\n      config = migrated.config;\n      const cleanedLattiz2 = await applyOneTimeLattiz2ImportCleanup(store, access, entry, config);\n      entry = cleanedLattiz2.entry;\n      config = cleanedLattiz2.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup }, 200, etag ? { etag } : {});"
    if text.count(old) != 1:
        raise SystemExit('GET cleanup-anker niet uniek')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
for needle in [CONST, MARKER, "cleanupNorm(fault?.brand) === 'lattiz2'", 'import volledig verwijderd', GET_MARKER]:
    if needle not in text:
        raise SystemExit(f'Buildvalidatie mislukt: {needle}')
print('[Machinepark] foutieve Lattiz2 storingsimport wordt eenmalig volledig verwijderd')
