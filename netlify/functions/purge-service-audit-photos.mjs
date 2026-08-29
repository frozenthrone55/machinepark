import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';
import { ROLE_CONFIG_KEY, defaultRoleConfig, hasPermission, normalizeRole, normalizeRoleConfig } from './_shared/permissions.mjs';

const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const STORE_NAME = 'machinepark-central';
const AUDIT_PREFIX = 'audit/';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };
const SERVICE_STORES = new Set(['maintenance', 'breakdowns']);

function json(data, status = 200) {
  return Response.json(data, { status, headers: NO_STORE });
}

async function authenticate(req, store) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });
  let verified;
  try { verified = await verifyToken(token, { secretKey }); }
  catch { throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 }); }
  if (!verified?.sub) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });
  const origin = req.headers.get('origin');
  if (origin && verified.azp && verified.azp !== origin) throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
  const clerk = createClerkClient({ secretKey });
  const user = await clerk.users.getUser(verified.sub);
  const emails = (user.emailAddresses || []).map((x) => String(x.emailAddress || '').trim().toLowerCase());
  const owner = emails.includes(ADMIN_EMAIL);
  const roleEntry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  const config = normalizeRoleConfig(roleEntry?.data || defaultRoleConfig());
  const role = normalizeRole(user?.publicMetadata?.role, { owner, config });
  return { sub: verified.sub, role, owner, config };
}

function withoutPhotos(item) {
  if (!item || typeof item !== 'object' || Array.isArray(item)) return item;
  const copy = { ...item };
  delete copy.photos;
  return copy;
}
function sanitizeUndo(undo, storeName, entityId) {
  if (!undo || undo.storeName !== storeName || undo.entityId !== entityId) return { undo, changed: false, removed: 0 };
  if (undo.kind === 'restore-deleted' && undo.beforeItem) {
    const count = Array.isArray(undo.beforeItem.photos) ? undo.beforeItem.photos.length : 0;
    if (!count && !Object.prototype.hasOwnProperty.call(undo.beforeItem, 'photos')) return { undo, changed: false, removed: 0 };
    return { undo: { ...undo, beforeItem: withoutPhotos(undo.beforeItem) }, changed: true, removed: count };
  }
  if (undo.kind === 'remove-added' && undo.expectedAfter) {
    const count = Array.isArray(undo.expectedAfter.photos) ? undo.expectedAfter.photos.length : 0;
    if (!count && !Object.prototype.hasOwnProperty.call(undo.expectedAfter, 'photos')) return { undo, changed: false, removed: 0 };
    return { undo: { ...undo, expectedAfter: withoutPhotos(undo.expectedAfter) }, changed: true, removed: count };
  }
  if (undo.kind === 'restore-fields' && Array.isArray(undo.fields)) {
    const photoFields = undo.fields.filter((field) => field?.key === 'photos');
    if (!photoFields.length) return { undo, changed: false, removed: 0 };
    const removed = photoFields.reduce((total, field) => total + (Array.isArray(field.beforeRaw) ? field.beforeRaw.length : 0) + (Array.isArray(field.afterRaw) ? field.afterRaw.length : 0), 0);
    const fields = undo.fields.filter((field) => field?.key !== 'photos');
    return { undo: fields.length ? { ...undo, fields } : null, changed: true, removed };
  }
  return { undo, changed: false, removed: 0 };
}
function sanitizeEntry(entry, storeName, entityId) {
  let changed = false;
  let removed = 0;
  const changes = (entry?.changes || []).map((change) => {
    const result = sanitizeUndo(change?.undo, storeName, entityId);
    if (!result.changed) return change;
    changed = true;
    removed += result.removed;
    const next = { ...change };
    if (result.undo) next.undo = result.undo;
    else delete next.undo;
    return next;
  });
  return { data: changed ? { ...entry, changes } : entry, changed, removed };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405);
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });
  try {
    const auth = await authenticate(req, store);
    const body = await req.json().catch(() => ({}));
    const storeName = String(body?.storeName || '');
    const entityId = String(body?.entityId || '').trim();
    if (!SERVICE_STORES.has(storeName) || !entityId) return json({ error: 'Ongeldig dossier.' }, 400);
    const permission = storeName === 'maintenance' ? 'maintenance.delete' : 'breakdowns.delete';
    if (!auth.owner && !hasPermission(auth.role, permission, auth.config)) {
      throw Object.assign(new Error('Deze rol mag dit dossier niet verwijderen.'), { status: 403 });
    }

    const { blobs } = await store.list({ prefix: AUDIT_PREFIX });
    let updatedEntries = 0;
    let removedPhotoPayloads = 0;
    for (const blob of blobs || []) {
      const current = await store.getWithMetadata(blob.key, { type: 'json', consistency: 'strong' });
      if (!current?.data) continue;
      const result = sanitizeEntry(current.data, storeName, entityId);
      if (!result.changed) continue;
      await store.setJSON(blob.key, result.data, { metadata: current.metadata || {} });
      updatedEntries += 1;
      removedPhotoPayloads += result.removed;
    }
    return json({ ok: true, updatedEntries, removedPhotoPayloads });
  } catch (error) {
    console.error('purge-service-audit-photos', error);
    return json({ error: error?.message || 'Opschonen van verslagfoto’s mislukt.' }, error?.status || 500);
  }
};
