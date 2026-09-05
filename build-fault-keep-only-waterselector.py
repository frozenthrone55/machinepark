from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'netlify/functions/fault-library.mjs'
text = path.read_text(encoding='utf-8')

CONST = "const FAULT_KEEP_ONLY_WATERSELECTOR_KEY = 'migration/fault-keep-only-00005-waterselector-bravilor-bolero-v1';"
if CONST not in text:
    anchor = "const LATTIZ2_IMPORT_CLEANUP_KEY = 'migration/fault-lattiz2-import-cleanup-v1';\n"
    if text.count(anchor) != 1:
        raise SystemExit('Globale storingsopschoning: const-anker niet uniek')
    text = text.replace(anchor, anchor + CONST + '\n', 1)

MARKER = 'async function applyOneTimeKeepOnlyWaterselectorCleanup('
if MARKER not in text:
    anchor = '\nexport default async (req) => {'
    helper = r'''

function isExactWaterselectorKeeper(fault) {
  const digits = String(fault?.code || '').replace(/\D/g, '');
  return (digits === '00005' || (digits !== '' && Number(digits) === 5))
    && cleanupNorm(fault?.name) === 'waterselector'
    && cleanupNorm(fault?.brand) === 'bravilor'
    && cleanupNorm(fault?.model) === 'bolero';
}

async function writeKeepOnlyWaterselectorAudit(store, auth, removed, kept) {
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
      changeCount: Math.max(1, removed.length),
      changes: [{
        entityType: 'Storingen',
        entityId: kept?.id || '00005-waterselector',
        entityLabel: 'Storingsbibliotheek opgeschoond',
        action: 'alles verwijderd behalve 00005 Waterselector',
        fields: [
          { field: 'Behouden', before: '—', after: '00005 — Waterselector — Bravilor — Bolero' },
          { field: 'Verwijderde storingen', before: String(removed.length), after: '0' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('keep-only Waterselector cleanup audit', error);
  }
}

async function applyOneTimeKeepOnlyWaterselectorCleanup(store, access, entry, config) {
  if (!canManage(access)) return { entry, config, cleanup: null };
  const migration = await store.get(FAULT_KEEP_ONLY_WATERSELECTOR_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
  if (migration?.done) return { entry, config, cleanup: migration };

  const candidates = config.faults
    .filter(isExactWaterselectorKeeper)
    .sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')));
  const kept = candidates[0] || null;

  // Veiligheid: niets verwijderen als de exact te behouden storing niet gevonden wordt.
  if (!kept) {
    return { entry, config, cleanup: { done: false, reason: '00005 Waterselector · Bravilor · Bolero niet gevonden' } };
  }

  const removed = config.faults.filter((fault) => fault.id !== kept.id);
  let nextEntry = entry;
  let nextConfig = config;
  if (removed.length) {
    nextEntry = await saveConfig(
      store,
      { version: 1, faults: [kept] },
      entry?.etag || null,
      entry?.etag || null,
    );
    nextConfig = normalizeConfig(nextEntry.data);
    await writeKeepOnlyWaterselectorAudit(store, access, removed, kept);
  }

  const cleanup = {
    done: true,
    at: new Date().toISOString(),
    removedCount: removed.length,
    keptId: kept.id,
    keptCode: kept.code || '00005',
    keptName: kept.name,
    keptBrand: kept.brand,
    keptModel: kept.model,
  };
  await store.setJSON(FAULT_KEEP_ONLY_WATERSELECTOR_KEY, cleanup, { metadata: { type: 'one-time-migration' } });
  return { entry: nextEntry, config: nextConfig, cleanup };
}
'''
    if text.count(anchor) != 1:
        raise SystemExit('Globale storingsopschoning: export-anker niet uniek')
    text = text.replace(anchor, helper + anchor, 1)

GET_MARKER = 'keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup'
if GET_MARKER not in text:
    old = "      const cleanedLattiz2 = await applyOneTimeLattiz2ImportCleanup(store, access, entry, config);\n      entry = cleanedLattiz2.entry;\n      config = cleanedLattiz2.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup }, 200, etag ? { etag } : {});"
    new = "      const cleanedLattiz2 = await applyOneTimeLattiz2ImportCleanup(store, access, entry, config);\n      entry = cleanedLattiz2.entry;\n      config = cleanedLattiz2.config;\n      const cleanedGlobal = await applyOneTimeKeepOnlyWaterselectorCleanup(store, access, entry, config);\n      entry = cleanedGlobal.entry;\n      config = cleanedGlobal.config;\n      const etag = entry?.etag || null;\n      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup, lattiz2Cleanup: cleanedLattiz2.cleanup, keepOnlyWaterselectorCleanup: cleanedGlobal.cleanup }, 200, etag ? { etag } : {});"
    if text.count(old) != 1:
        raise SystemExit('Globale storingsopschoning: GET-anker niet uniek')
    text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
for needle in [CONST, MARKER, 'isExactWaterselectorKeeper', "cleanupNorm(fault?.brand) === 'bravilor'", "cleanupNorm(fault?.model) === 'bolero'", '{ version: 1, faults: [kept] }', GET_MARKER]:
    if needle not in text:
        raise SystemExit(f'Buildvalidatie mislukt: {needle}')
print('[Machinepark] storingsbibliotheek wordt eenmalig leeggemaakt behalve 00005 Waterselector · Bravilor · Bolero')
