from pathlib import Path

ROOT = Path(__file__).resolve().parent
endpoint_path = ROOT / 'netlify/functions/machinepark-data.mjs'
endpoint = endpoint_path.read_text(encoding='utf-8')

CONST = "const PLACEMENT_WORKS_MIGRATION_KEY = 'migration/classify-wcl0685-wcl0678-wcl0684-placement-2026-09-01-1538-v1';"
if CONST not in endpoint:
    anchor = "const CLEAR_SERVICE_DATES_MIGRATION_KEY = 'migration/clear-service-dates-2026-08-25-v1';\n"
    if endpoint.count(anchor) != 1:
        raise SystemExit('Plaatsingsmigratie: const-anker niet uniek')
    endpoint = endpoint.replace(anchor, anchor + CONST + '\n', 1)

LABEL_MARKER = "workTypeName: 'Type werkzaamheden'"
if LABEL_MARKER not in endpoint:
    old = "  hours: 'Werkduur', batchSize: 'Aantal toestellen'\n};"
    new = "  hours: 'Werkduur', batchSize: 'Aantal toestellen', serviceKind: 'Soort registratie', workTypeName: 'Type werkzaamheden'\n};"
    if endpoint.count(old) != 1:
        raise SystemExit('Plaatsingsmigratie: veldlabel-anker niet uniek')
    endpoint = endpoint.replace(old, new, 1)

ENTITY_MARKER = "item.serviceKind === 'other' ? (item.workTypeName || 'Andere werken') : (item.issue || 'Depannage')"
if ENTITY_MARKER not in endpoint:
    old = "  if (storeName === 'breakdowns') return `${item.issue || 'Depannage'} · ${deviceLabel(snapshot, item.deviceId)}`;"
    new = "  if (storeName === 'breakdowns') return `${item.serviceKind === 'other' ? (item.workTypeName || 'Andere werken') : (item.issue || 'Depannage')} · ${deviceLabel(snapshot, item.deviceId)}`;"
    if endpoint.count(old) != 1:
        raise SystemExit('Plaatsingsmigratie: entiteitslabel-anker niet uniek')
    endpoint = endpoint.replace(old, new, 1)

HELPER_MARKER = 'async function classifySelectedPlacementsOnce('
if HELPER_MARKER not in endpoint:
    anchor = '\nfunction accessPayload(auth) {'
    helper = r'''

async function classifySelectedPlacementsOnce(store, auth) {
  const marker = await store.getWithMetadata(PLACEMENT_WORKS_MIGRATION_KEY, { type: 'json', consistency: 'strong' });
  if (marker?.data?.done) return marker.data;

  const current = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong' });
  if (!current?.data || !Array.isArray(current.data.devices) || !Array.isArray(current.data.breakdowns)) return null;

  const before = current.data;
  const targetAssets = new Set(['WCL0685', 'WCL0678', 'WCL0684']);
  const assetByDeviceId = new Map((before.devices || []).map((device) => [device.id, String(device.assetCode || '').trim().toUpperCase()]));
  const candidates = new Map();
  let ambiguous = false;

  for (const record of before.breakdowns) {
    if (!record || record.isDraft === true) continue;
    const assetCode = assetByDeviceId.get(record.deviceId) || '';
    if (!targetAssets.has(assetCode)) continue;
    const sameDate = String(record.date || '') === '2026-09-01';
    const sameTime = String(record.time || '').slice(0, 5) === '15:38';
    const sameWork = String(record.issue || '').trim().toLocaleLowerCase('nl-BE') === 'plaatsing';
    if (!sameDate || !sameTime || !sameWork) continue;
    if (candidates.has(assetCode)) { ambiguous = true; break; }
    candidates.set(assetCode, record);
  }

  if (ambiguous || candidates.size !== targetAssets.size) {
    console.warn('Plaatsingsmigratie niet uitgevoerd: de drie registraties konden niet eenduidig worden gevonden.', {
      found: [...candidates.keys()], ambiguous,
    });
    return null;
  }

  let changedRecords = 0;
  const breakdowns = before.breakdowns.map((record) => {
    const assetCode = assetByDeviceId.get(record?.deviceId) || '';
    if (!candidates.has(assetCode) || candidates.get(assetCode)?.id !== record?.id) return record;
    if (record.serviceKind === 'other' && String(record.workTypeName || '').trim() === 'Plaatsing') return record;
    changedRecords += 1;
    // Bewaar het volledige bestaande record (foto's, onderdelen, werkbon, uren, notities, enz.)
    // en wijzig uitsluitend de classificatie.
    return { ...record, serviceKind: 'other', workTypeName: 'Plaatsing' };
  });

  const at = new Date().toISOString();
  if (changedRecords) {
    const after = { ...before, breakdowns, updatedAt: at, updatedBy: auth.sub, updatedByEmail: auth.email || '' };
    const result = await store.setJSON(STATE_KEY, after, {
      onlyIfMatch: current.etag,
      metadata: { updatedAt: at, updatedBy: auth.sub, updatedByEmail: auth.email || '' },
    });
    if (!result.modified) return null;
    try { await writeAudit(store, auth, before, after); } catch (auditError) { console.error('plaatsingsmigratie audit logging', auditError); }
  }

  const migration = {
    done: true,
    at,
    changedRecords,
    assetCodes: [...targetAssets],
    date: '2026-09-01',
    time: '15:38',
    classification: 'Plaatsing',
  };
  await store.setJSON(PLACEMENT_WORKS_MIGRATION_KEY, migration, { metadata: { type: 'one-time-migration' } });
  return migration;
}
'''
    if endpoint.count(anchor) != 1:
        raise SystemExit('Plaatsingsmigratie: helper-anker niet uniek')
    endpoint = endpoint.replace(anchor, helper + anchor, 1)

CALL_MARKER = 'await classifySelectedPlacementsOnce(store, auth);'
if CALL_MARKER not in endpoint:
    old = "      await clearServiceDatesOnce(store, auth);\n      const cachedEtag = req.headers.get('if-none-match') || undefined;"
    new = "      await clearServiceDatesOnce(store, auth);\n      await classifySelectedPlacementsOnce(store, auth);\n      const cachedEtag = req.headers.get('if-none-match') || undefined;"
    if endpoint.count(old) != 1:
        raise SystemExit('Plaatsingsmigratie: GET-anker niet uniek')
    endpoint = endpoint.replace(old, new, 1)

endpoint_path.write_text(endpoint, encoding='utf-8')

built = endpoint_path.read_text(encoding='utf-8')
required = [
    CONST,
    HELPER_MARKER,
    CALL_MARKER,
    "new Set(['WCL0685', 'WCL0678', 'WCL0684'])",
    "String(record.date || '') === '2026-09-01'",
    "String(record.time || '').slice(0, 5) === '15:38'",
    "=== 'plaatsing'",
    "return { ...record, serviceKind: 'other', workTypeName: 'Plaatsing' };",
    'candidates.size !== targetAssets.size',
    LABEL_MARKER,
    ENTITY_MARKER,
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: plaatsingsmigratie ontbreekt ({needle})')

print('[Machinepark] WCL0685, WCL0678 en WCL0684 van 01/09/2026 15:38 worden eenmalig als Plaatsing geclassificeerd met behoud van alle recordgegevens')
