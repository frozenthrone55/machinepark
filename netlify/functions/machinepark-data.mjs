import { getStore } from '@netlify/blobs';
import {
  assertSnapshotWriteAllowed,
  roleLabel,
  validSnapshot,
} from './_shared/permissions.mjs';
import { cleanupRemovedEntityPhotos } from './_shared/photo-cleanup.mjs';
import {
  ADMIN_EMAIL,
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const STATE_KEY = 'state-v1';
const AUDIT_PREFIX = 'audit/';
const CLEAR_SERVICE_DATES_MIGRATION_KEY = 'migration/clear-service-dates-2026-08-25-v1';

const FIELD_LABELS = {
  assetCode: 'WCL nr.', location: 'Locatie', brand: 'Merk', model: 'Model', serial: 'Serienummer',
  installDate: 'Installatiedatum', status: 'Status', nextHalf: 'Volgend halfjaarlijks onderhoud',
  nextAnnual: 'Volgend jaarlijks onderhoud', notes: 'Notities', type: 'Type', date: 'Datum', time: 'Tijd',
  technician: 'Technieker', issue: 'Storing', diagnosis: 'Diagnose', solution: 'Oplossing', priority: 'Prioriteit',
  artNr: 'Artikelnummer', description: 'Omschrijving', deviceBrand: 'Merk toestel', price: 'Prijs', stock: 'Voorraad',
  minStock: 'Minimumvoorraad', supplierCode: 'Code leverancier', warehouse: 'Magazijnlocatie', usedParts: 'Gebruikte onderdelen',
  locationHistory: 'Locatiehistoriek', deviceChangeLog: 'Toestelwijzigingen', photo: 'Foto', photos: 'Foto’s verslag',
  hours: 'Werkduur', batchSize: 'Aantal toestellen'
};
const IGNORED_FIELDS = new Set(['id', 'createdAt', 'updatedAt', 'sourceInventory', 'redInventoryStatusApplied']);

function shortValue(value) {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return `${value.length} item(s)`;
  if (typeof value === 'object') return 'gewijzigd';
  const text = String(value);
  if (text.startsWith('data:image/')) return 'foto';
  return text.length > 100 ? text.slice(0, 97) + '…' : text;
}

function changedFields(before, after) {
  const keys = new Set([...Object.keys(before || {}), ...Object.keys(after || {})]);
  const result = [];
  for (const key of keys) {
    if (IGNORED_FIELDS.has(key)) continue;
    const beforeExists = Object.prototype.hasOwnProperty.call(before || {}, key);
    const afterExists = Object.prototype.hasOwnProperty.call(after || {}, key);
    const a = before?.[key];
    const b = after?.[key];
    if (JSON.stringify(a) === JSON.stringify(b) && beforeExists === afterExists) continue;
    result.push({ key, field: FIELD_LABELS[key] || key, before: shortValue(a), after: shortValue(b), beforeExists, afterExists, beforeRaw: a === undefined ? null : a, afterRaw: b === undefined ? null : b });
  }
  return result;
}

function deviceLabel(snapshot, deviceId) {
  const d = (snapshot?.devices || []).find((x) => x.id === deviceId);
  return d ? [d.assetCode, d.location || '', d.brand || '', d.model || ''].filter(Boolean).join(' · ') : 'Onbekend toestel';
}
function entityLabel(storeName, item, snapshot) {
  if (!item) return 'Onbekend';
  if (storeName === 'devices') return item.assetCode || item.model || item.id;
  if (storeName === 'parts') return [item.artNr, item.description].filter(Boolean).join(' · ') || item.id;
  if (storeName === 'maintenance') return `${item.type || 'Onderhoud'} · ${deviceLabel(snapshot, item.deviceId)}`;
  if (storeName === 'breakdowns') return `${item.issue || 'Depannage'} · ${deviceLabel(snapshot, item.deviceId)}`;
  return item.id || 'Item';
}
const ENTITY_NAMES = { devices: 'Toestel', parts: 'Onderdeel', maintenance: 'Onderhoud', breakdowns: 'Depannage' };

function diffSnapshots(before, after) {
  if (!before) return [{ entityType: 'Systeem', entityId: 'state-v1', entityLabel: 'Centrale Machinepark-database', action: 'geïnitialiseerd', fields: [] }];
  const changes = [];
  for (const storeName of ['devices', 'maintenance', 'breakdowns', 'parts']) {
    const oldMap = new Map((before[storeName] || []).map((x) => [x.id, x]));
    const newMap = new Map((after[storeName] || []).map((x) => [x.id, x]));
    for (const [id, item] of newMap) {
      if (!oldMap.has(id)) {
        changes.push({ entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, after), action: 'toegevoegd', fields: [], undo: { kind: 'remove-added', storeName, entityId: id, expectedAfter: item } });
        continue;
      }
      const fields = changedFields(oldMap.get(id), item);
      if (fields.length) {
        changes.push({
          entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, after), action: 'gewijzigd',
          fields: fields.map(({ key, beforeExists, afterExists, beforeRaw, afterRaw, ...display }) => display),
          undo: { kind: 'restore-fields', storeName, entityId: id, fields: fields.map(({ key, beforeExists, afterExists, beforeRaw, afterRaw }) => ({ key, beforeExists, afterExists, beforeRaw, afterRaw })) },
        });
      }
    }
    for (const [id, item] of oldMap) {
      if (!newMap.has(id)) changes.push({ entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, before), action: 'verwijderd', fields: [], undo: { kind: 'restore-deleted', storeName, entityId: id, beforeItem: item } });
    }
  }
  return changes;
}

async function writeAudit(store, auth, before, after) {
  const changes = diffSnapshots(before, after);
  if (!changes.length) return;
  const at = new Date().toISOString();
  const id = crypto.randomUUID();
  const entry = {
    id, at, userId: auth.sub, userEmail: auth.email || auth.sub, userName: auth.name || '', userRole: auth.role || 'gebruiker',
    changeCount: changes.length, changes: changes.slice(0, 500), truncated: changes.length > 500, reversibleSchema: 1,
  };
  await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, entry, { metadata: { at, userId: auth.sub, userEmail: auth.email || '' } });
}

async function clearServiceDatesOnce(store, auth) {
  if (String(auth?.email || '').toLowerCase() !== ADMIN_EMAIL) return;
  const marker = await store.getWithMetadata(CLEAR_SERVICE_DATES_MIGRATION_KEY, { type: 'json', consistency: 'strong' });
  if (marker) return;
  const current = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong' });
  if (!current?.data || !Array.isArray(current.data.devices)) return;
  const before = current.data;
  let changedDevices = 0;
  const devices = before.devices.map((device) => {
    if (!device?.nextHalf && !device?.nextAnnual) return device;
    changedDevices += 1;
    return { ...device, nextHalf: '', nextAnnual: '', updatedAt: new Date().toISOString() };
  });
  if (!changedDevices) {
    await store.setJSON(CLEAR_SERVICE_DATES_MIGRATION_KEY, { done: true, at: new Date().toISOString(), changedDevices: 0 });
    return;
  }
  const after = { ...before, devices, updatedAt: new Date().toISOString(), updatedBy: auth.sub, updatedByEmail: auth.email || '' };
  const result = await store.setJSON(STATE_KEY, after, { onlyIfMatch: current.etag, metadata: { updatedAt: after.updatedAt, updatedBy: auth.sub, updatedByEmail: auth.email || '' } });
  if (!result.modified) return;
  try { await writeAudit(store, auth, before, after); } catch (auditError) { console.error('machinepark migration audit logging', auditError); }
  await store.setJSON(CLEAR_SERVICE_DATES_MIGRATION_KEY, { done: true, at: after.updatedAt, changedDevices, performedBy: auth.email || auth.sub });
}

function accessPayload(auth) {
  return {
    role: auth.role,
    roleLabel: roleLabel(auth.role, auth.roleConfig),
    permissions: auth.permissions,
    roleConfigEtag: auth.roleConfigEtag,
  };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  try {
    const store = getStore({ name: STORE_NAME, consistency: 'strong' });
    const auth = await resolveRoleAccess(store, await authenticateClerk(req));

    if (req.method === 'GET') {
      await clearServiceDatesOnce(store, auth);
      const cachedEtag = req.headers.get('if-none-match') || undefined;
      const entry = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong', etag: cachedEtag });
      if (!entry) return json({ exists: false, etag: null, ...accessPayload(auth) });
      if (cachedEtag && entry.etag === cachedEtag && entry.data === null) {
        return json({ exists: true, unchanged: true, etag: entry.etag, data: null, ...accessPayload(auth) }, 200, { etag: entry.etag });
      }
      return json({ exists: true, etag: entry.etag, data: entry.data, ...accessPayload(auth) }, 200, { etag: entry.etag });
    }

    if (req.method === 'PUT') {
      const body = await req.json();
      const data = body?.data;
      const expectedEtag = body?.etag || null;
      if (!validSnapshot(data)) return json({ error: 'Ongeldige Machinepark-gegevens.' }, 400);
      const previousEntry = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong' });
      const previousData = previousEntry?.data || null;
      assertSnapshotWriteAllowed(previousData, data, auth.role, auth.roleConfig, { owner: auth.owner });
      data.updatedAt = new Date().toISOString();
      data.updatedBy = auth.sub;
      data.updatedByEmail = auth.email || '';
      const metadata = { updatedAt: data.updatedAt, updatedBy: auth.sub, updatedByEmail: auth.email || '' };
      const options = expectedEtag ? { onlyIfMatch: expectedEtag, metadata } : { onlyIfNew: true, metadata };
      const result = await store.setJSON(STATE_KEY, data, options);
      if (!result.modified) {
        const current = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
        return json({ error: 'De centrale gegevens zijn intussen gewijzigd.', etag: current?.etag || null }, 409);
      }
      try { await writeAudit(store, auth, previousData, data); } catch (auditError) { console.error('machinepark audit logging', auditError); }
      try {
        const cleanup = await cleanupRemovedEntityPhotos(store, previousData, data);
        if (cleanup.blobs) console.info('machinepark foto-opruiming', cleanup);
      } catch (cleanupError) {
        console.error('machinepark foto-opruiming mislukt', cleanupError);
        return json({ error: 'De gegevens zijn verwijderd, maar de gekoppelde foto-opruiming kon niet volledig worden afgerond. Probeer de verwijdering/verversing opnieuw.' }, 500);
      }
      const current = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
      return json({ ok: true, etag: current?.etag || null, updatedAt: data.updatedAt, ...accessPayload(auth) });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, PUT, OPTIONS' });
  } catch (error) {
    console.error('machinepark-data', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
