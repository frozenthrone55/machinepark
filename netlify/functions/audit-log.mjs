import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';

const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const STORE_NAME = 'machinepark-central';
const STATE_KEY = 'state-v1';
const AUDIT_PREFIX = 'audit/';
const UNDO_PREFIX = 'audit-undo/';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };
const VALID_STORES = new Set(['devices', 'parts', 'maintenance', 'breakdowns']);

function json(data, status = 200, headers = {}) {
  return Response.json(data, { status, headers: { ...NO_STORE, ...headers } });
}

function emailsOf(user) {
  return (user?.emailAddresses || []).map((x) => String(x.emailAddress || '').trim().toLowerCase()).filter(Boolean);
}

function isAdminUser(user) {
  if (emailsOf(user).includes(ADMIN_EMAIL)) return true;
  return String(user?.publicMetadata?.role || '').trim().toLowerCase() === 'beheerder';
}

async function authenticateAdmin(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });

  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });

  let verified;
  try {
    verified = await verifyToken(token, { secretKey });
  } catch {
    throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 });
  }
  if (!verified?.sub) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });

  const origin = req.headers.get('origin');
  if (origin && verified.azp && verified.azp !== origin) {
    throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
  }

  const clerk = createClerkClient({ secretKey });
  const currentUser = await clerk.users.getUser(verified.sub);
  if (!isAdminUser(currentUser)) {
    throw Object.assign(new Error('Alleen een beheerder heeft toegang tot het logboek.'), { status: 403 });
  }
  const primary = (currentUser.emailAddresses || []).find((x) => x.id === currentUser.primaryEmailAddressId);
  const email = String(primary?.emailAddress || currentUser.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
  const name = [currentUser.firstName, currentUser.lastName].filter(Boolean).join(' ').trim();
  return { sub: verified.sub, email, name };
}

function deepEqual(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

function hasOwn(obj, key) {
  return Object.prototype.hasOwnProperty.call(obj || {}, key);
}

function reverseFieldsForDisplay(change) {
  return (change?.fields || []).map((f) => ({ field: f.field, before: f.after, after: f.before }));
}

function inverseUndoPayload(undo) {
  if (!undo) return null;
  if (undo.kind === 'restore-fields') {
    return {
      kind: 'restore-fields',
      storeName: undo.storeName,
      entityId: undo.entityId,
      fields: (undo.fields || []).map((f) => ({
        key: f.key,
        beforeExists: f.afterExists,
        afterExists: f.beforeExists,
        beforeRaw: f.afterRaw,
        afterRaw: f.beforeRaw,
      })),
    };
  }
  if (undo.kind === 'remove-added') {
    return { kind: 'restore-deleted', storeName: undo.storeName, entityId: undo.entityId, beforeItem: undo.expectedAfter };
  }
  if (undo.kind === 'restore-deleted') {
    return { kind: 'remove-added', storeName: undo.storeName, entityId: undo.entityId, expectedAfter: undo.beforeItem };
  }
  return null;
}

function applyUndoToSnapshot(snapshot, change) {
  const undo = change?.undo;
  if (!undo || !VALID_STORES.has(undo.storeName) || !undo.entityId) {
    throw Object.assign(new Error('Deze oudere logboekregel bevat geen volledige hersteldata.'), { status: 409 });
  }

  const list = Array.isArray(snapshot[undo.storeName]) ? snapshot[undo.storeName].map((x) => ({ ...x })) : [];
  const index = list.findIndex((x) => x.id === undo.entityId);
  const now = new Date().toISOString();

  if (undo.kind === 'restore-fields') {
    if (index < 0) throw Object.assign(new Error('Dit item bestaat niet meer. De wijziging kan niet veilig worden teruggedraaid.'), { status: 409 });
    const current = list[index];
    for (const field of undo.fields || []) {
      const currentExists = hasOwn(current, field.key);
      if (currentExists !== Boolean(field.afterExists)) {
        throw Object.assign(new Error(`Het veld “${field.key}” is intussen opnieuw gewijzigd. Ongedaan maken is daarom geblokkeerd.`), { status: 409 });
      }
      if (field.afterExists && !deepEqual(current[field.key], field.afterRaw)) {
        throw Object.assign(new Error(`Het veld “${field.key}” is intussen opnieuw gewijzigd. Ongedaan maken is daarom geblokkeerd.`), { status: 409 });
      }
    }
    const restored = { ...current };
    for (const field of undo.fields || []) {
      if (field.beforeExists) restored[field.key] = field.beforeRaw;
      else delete restored[field.key];
    }
    restored.updatedAt = now;
    list[index] = restored;
  } else if (undo.kind === 'remove-added') {
    if (index < 0) throw Object.assign(new Error('Dit toegevoegde item is al verwijderd.'), { status: 409 });
    if (!deepEqual(list[index], undo.expectedAfter)) {
      throw Object.assign(new Error('Dit item is na de oorspronkelijke toevoeging nog gewijzigd. Verwijderen via het oude logboek is daarom geblokkeerd.'), { status: 409 });
    }
    list.splice(index, 1);
  } else if (undo.kind === 'restore-deleted') {
    if (index >= 0) throw Object.assign(new Error('Er bestaat intussen opnieuw een item met hetzelfde ID. Herstellen is daarom geblokkeerd.'), { status: 409 });
    if (!undo.beforeItem) throw Object.assign(new Error('De oorspronkelijke gegevens ontbreken in deze logboekregel.'), { status: 409 });
    list.push({ ...undo.beforeItem });
  } else {
    throw Object.assign(new Error('Dit type wijziging kan niet ongedaan worden gemaakt.'), { status: 409 });
  }

  return { ...snapshot, [undo.storeName]: list };
}

async function writeUndoAudit(store, auth, originalEntry, change, changeIndex) {
  const at = new Date().toISOString();
  const id = crypto.randomUUID();
  const inverseUndo = inverseUndoPayload(change.undo);
  const undoChange = {
    entityType: change.entityType,
    entityId: change.entityId,
    entityLabel: change.entityLabel,
    action: 'ongedaan gemaakt',
    fields: reverseFieldsForDisplay(change),
    undo: inverseUndo,
    undoOf: { entryId: originalEntry.id, changeIndex },
  };
  const entry = {
    id,
    at,
    userId: auth.sub,
    userEmail: auth.email || auth.sub,
    userName: auth.name || '',
    changeCount: 1,
    changes: [undoChange],
    reversibleSchema: 1,
    operation: 'undo',
  };
  await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, entry, {
    metadata: { at, userId: auth.sub, userEmail: auth.email || '', operation: 'undo' },
  });
}

async function getAuditEntry(store, auditKey) {
  if (!auditKey || !String(auditKey).startsWith(AUDIT_PREFIX)) {
    throw Object.assign(new Error('Ongeldige logboekregel.'), { status: 400 });
  }
  const entry = await store.getWithMetadata(auditKey, { type: 'json', consistency: 'strong' });
  if (!entry?.data) throw Object.assign(new Error('Logboekregel niet gevonden.'), { status: 404 });
  return entry;
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });

  try {
    const auth = await authenticateAdmin(req);
    const store = getStore({ name: STORE_NAME, consistency: 'strong' });

    if (req.method === 'GET') {
      const [{ blobs }, { blobs: undoBlobs }] = await Promise.all([
        store.list({ prefix: AUDIT_PREFIX }),
        store.list({ prefix: UNDO_PREFIX }),
      ]);
      const undone = new Set((undoBlobs || []).map((b) => b.key.slice(UNDO_PREFIX.length)));
      const selected = [...(blobs || [])].sort((a, b) => b.key.localeCompare(a.key)).slice(0, 250);

      const entries = await Promise.all(selected.map(async ({ key }) => {
        try {
          const entry = await store.getWithMetadata(key, { type: 'json', consistency: 'strong' });
          if (!entry?.data) return null;
          const data = entry.data;
          return {
            ...data,
            auditKey: key,
            changes: (data.changes || []).map((change, index) => {
              const markerId = `${data.id}/${index}`;
              const { undo, ...safeChange } = change || {};
              return {
                ...safeChange,
                reversible: Boolean(undo) && !undone.has(markerId),
                undone: undone.has(markerId),
              };
            }),
          };
        } catch (error) {
          console.error('audit entry lezen', key, error);
          return null;
        }
      }));

      return json({ entries: entries.filter(Boolean) });
    }

    if (req.method === 'POST') {
      const body = await req.json().catch(() => ({}));
      const auditKey = String(body?.auditKey || '');
      const changeIndex = Number(body?.changeIndex);
      if (!Number.isInteger(changeIndex) || changeIndex < 0) return json({ error: 'Ongeldige wijzigingsregel.' }, 400);

      const auditEntry = await getAuditEntry(store, auditKey);
      const originalEntry = auditEntry.data;
      const change = originalEntry?.changes?.[changeIndex];
      if (!change) return json({ error: 'Wijziging niet gevonden in deze logboekregel.' }, 404);
      if (!change.undo) return json({ error: 'Deze oudere logboekregel bevat geen volledige hersteldata.' }, 409);

      const markerKey = `${UNDO_PREFIX}${originalEntry.id}/${changeIndex}`;
      const marker = await store.getWithMetadata(markerKey, { type: 'json', consistency: 'strong' });
      if (marker) return json({ error: 'Deze wijziging is al ongedaan gemaakt.' }, 409);

      const current = await store.getWithMetadata(STATE_KEY, { type: 'json', consistency: 'strong' });
      if (!current?.data) return json({ error: 'Centrale Machinepark-gegevens niet gevonden.' }, 404);

      const before = current.data;
      const after = applyUndoToSnapshot(before, change);
      after.updatedAt = new Date().toISOString();
      after.updatedBy = auth.sub;
      after.updatedByEmail = auth.email || '';

      const result = await store.setJSON(STATE_KEY, after, {
        onlyIfMatch: current.etag,
        metadata: { updatedAt: after.updatedAt, updatedBy: auth.sub, updatedByEmail: auth.email || '' },
      });
      if (!result.modified) return json({ error: 'De centrale gegevens zijn intussen gewijzigd. Vernieuw en probeer opnieuw.' }, 409);

      await store.setJSON(markerKey, {
        at: after.updatedAt,
        by: auth.email || auth.sub,
        auditEntryId: originalEntry.id,
        changeIndex,
      });

      try {
        await writeUndoAudit(store, auth, originalEntry, change, changeIndex);
      } catch (auditError) {
        console.error('undo audit logging', auditError);
      }

      const latest = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
      return json({ ok: true, etag: latest?.etag || null, updatedAt: after.updatedAt });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, OPTIONS' });
  } catch (error) {
    console.error('audit-log', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
