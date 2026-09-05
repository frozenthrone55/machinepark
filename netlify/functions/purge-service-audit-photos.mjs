import { getStore } from '@netlify/blobs';
import { hasPermission } from './_shared/permissions.mjs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const AUDIT_PREFIX = 'audit/';
const SERVICE_STORES = new Set(['maintenance', 'breakdowns']);

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
    const auth = await resolveRoleAccess(store, await authenticateClerk(req));
    const body = await req.json().catch(() => ({}));
    const storeName = String(body?.storeName || '');
    const entityId = String(body?.entityId || '').trim();
    if (!SERVICE_STORES.has(storeName) || !entityId) return json({ error: 'Ongeldig dossier.' }, 400);
    const permission = storeName === 'maintenance' ? 'maintenance.delete' : 'breakdowns.delete';
    if (!auth.owner && !hasPermission(auth.role, permission, auth.roleConfig)) {
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
