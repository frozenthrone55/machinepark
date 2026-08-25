import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';

const STORE_NAME = 'machinepark-central';
const STATE_KEY = 'state-v1';
const AUDIT_PREFIX = 'audit/';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };

function json(data, status = 200, headers = {}) {
  return Response.json(data, { status, headers: { ...NO_STORE, ...headers } });
}

async function authenticate(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) {
    throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  }

  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) {
    throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });
  }

  try {
    const verified = await verifyToken(token, { secretKey });
    if (!verified?.sub) throw new Error('Geen gebruiker in token.');

    const origin = req.headers.get('origin');
    if (origin && verified.azp && verified.azp !== origin) {
      throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
    }

    const clerk = createClerkClient({ secretKey });
    const user = await clerk.users.getUser(verified.sub);
    const primary = (user.emailAddresses || []).find((x) => x.id === user.primaryEmailAddressId);
    const email = String(primary?.emailAddress || user.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
    const name = [user.firstName, user.lastName].filter(Boolean).join(' ').trim();
    return { ...verified, email, name };
  } catch (error) {
    if (error?.status) throw error;
    throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 });
  }
}

function validSnapshot(data) {
  return Boolean(
    data &&
    data.app === 'Machinepark' &&
    Number(data.schema) === 1 &&
    Array.isArray(data.parts) &&
    Array.isArray(data.devices) &&
    Array.isArray(data.maintenance) &&
    Array.isArray(data.breakdowns)
  );
}

const FIELD_LABELS = {
  assetCode: 'WCL nr.', location: 'Locatie', brand: 'Merk', model: 'Model', serial: 'Serienummer',
  installDate: 'Installatiedatum', status: 'Status', nextHalf: 'Volgend halfjaarlijks onderhoud',
  nextAnnual: 'Volgend jaarlijks onderhoud', notes: 'Notities', type: 'Type', date: 'Datum', time: 'Tijd',
  technician: 'Technieker', issue: 'Storing', diagnosis: 'Diagnose', solution: 'Oplossing', priority: 'Prioriteit',
  artNr: 'Artikelnummer', description: 'Omschrijving', deviceBrand: 'Merk toestel', price: 'Prijs', stock: 'Voorraad',
  minStock: 'Minimumvoorraad', supplierCode: 'Code leverancier', warehouse: 'Magazijnlocatie', usedParts: 'Gebruikte onderdelen',
  locationHistory: 'Locatiehistoriek', deviceChangeLog: 'Toestelwijzigingen', photo: 'Foto'
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
    const a = before?.[key];
    const b = after?.[key];
    if (JSON.stringify(a) === JSON.stringify(b)) continue;
    result.push({
      field: FIELD_LABELS[key] || key,
      before: shortValue(a),
      after: shortValue(b),
    });
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

const ENTITY_NAMES = {
  devices: 'Toestel', parts: 'Onderdeel', maintenance: 'Onderhoud', breakdowns: 'Depannage'
};

function diffSnapshots(before, after) {
  if (!before) {
    return [{ entityType: 'Systeem', entityId: 'state-v1', entityLabel: 'Centrale Machinepark-database', action: 'geïnitialiseerd', fields: [] }];
  }

  const changes = [];
  for (const storeName of ['devices', 'maintenance', 'breakdowns', 'parts']) {
    const oldMap = new Map((before[storeName] || []).map((x) => [x.id, x]));
    const newMap = new Map((after[storeName] || []).map((x) => [x.id, x]));

    for (const [id, item] of newMap) {
      if (!oldMap.has(id)) {
        changes.push({ entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, after), action: 'toegevoegd', fields: [] });
        continue;
      }
      const fields = changedFields(oldMap.get(id), item);
      if (fields.length) {
        changes.push({ entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, after), action: 'gewijzigd', fields });
      }
    }

    for (const [id, item] of oldMap) {
      if (!newMap.has(id)) {
        changes.push({ entityType: ENTITY_NAMES[storeName], entityId: id, entityLabel: entityLabel(storeName, item, before), action: 'verwijderd', fields: [] });
      }
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
    id,
    at,
    userId: auth.sub,
    userEmail: auth.email || auth.sub,
    userName: auth.name || '',
    changeCount: changes.length,
    changes: changes.slice(0, 500),
    truncated: changes.length > 500,
  };
  await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, entry, { metadata: { at, userId: auth.sub, userEmail: auth.email || '' } });
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });

  try {
    const auth = await authenticate(req);
    const store = getStore({ name: STORE_NAME, consistency: 'strong' });

    if (req.method === 'GET') {
      const cachedEtag = req.headers.get('if-none-match') || undefined;
      const entry = await store.getWithMetadata(STATE_KEY, {
        type: 'json',
        consistency: 'strong',
        etag: cachedEtag,
      });

      if (!entry) return json({ exists: false, etag: null });
      if (cachedEtag && entry.etag === cachedEtag && entry.data === null) {
        return new Response(null, { status: 304, headers: { ...NO_STORE, etag: entry.etag } });
      }

      return json(
        { exists: true, etag: entry.etag, data: entry.data },
        200,
        { etag: entry.etag }
      );
    }

    if (req.method === 'PUT') {
      const body = await req.json();
      const data = body?.data;
      const expectedEtag = body?.etag || null;
      if (!validSnapshot(data)) return json({ error: 'Ongeldige Machinepark-gegevens.' }, 400);

      const previousEntry = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong' });
      const previousData = previousEntry?.data || null;

      data.updatedAt = new Date().toISOString();
      data.updatedBy = auth.sub;
      data.updatedByEmail = auth.email || '';

      const metadata = { updatedAt: data.updatedAt, updatedBy: auth.sub, updatedByEmail: auth.email || '' };
      const options = expectedEtag
        ? { onlyIfMatch: expectedEtag, metadata }
        : { onlyIfNew: true, metadata };

      const result = await store.setJSON(STATE_KEY, data, options);
      if (!result.modified) {
        const current = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
        return json(
          { error: 'De centrale gegevens zijn intussen gewijzigd.', etag: current?.etag || null },
          409
        );
      }

      try {
        await writeAudit(store, auth, previousData, data);
      } catch (auditError) {
        console.error('machinepark audit logging', auditError);
      }

      const current = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
      return json({ ok: true, etag: current?.etag || null, updatedAt: data.updatedAt });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, PUT, OPTIONS' });
  } catch (error) {
    console.error('machinepark-data', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
