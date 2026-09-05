const DEVICE_PHOTO_PREFIX = 'device-photos/';
const PART_PHOTO_PREFIX = 'part-photos/';
const SERVICE_PHOTO_PREFIX = 'service-photos/';

export function safePhotoOwnerId(value) {
  return String(value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100);
}

function idsOf(list) {
  return new Set((Array.isArray(list) ? list : []).map((item) => String(item?.id || '').trim()).filter(Boolean));
}

async function deletePrefix(store, prefix) {
  const listed = await store.list({ prefix });
  const keys = (listed?.blobs || []).map((item) => item.key).filter(Boolean);
  if (keys.length) await Promise.all(keys.map((key) => store.delete(key)));
  return keys.length;
}

export function removedPhotoOwners(before, after) {
  const collections = ['devices', 'parts', 'maintenance', 'breakdowns'];
  return Object.fromEntries(collections.map((name) => {
    const previous = idsOf(before?.[name]);
    const next = idsOf(after?.[name]);
    return [name, [...previous].filter((id) => !next.has(id))];
  }));
}

export async function cleanupRemovedEntityPhotos(store, before, after) {
  if (!before || !after) return { devices: 0, parts: 0, maintenance: 0, breakdowns: 0, blobs: 0 };
  const removed = removedPhotoOwners(before, after);
  let blobs = 0;
  for (const id of removed.devices) blobs += await deletePrefix(store, `${DEVICE_PHOTO_PREFIX}${safePhotoOwnerId(id)}/`);
  for (const id of removed.parts) blobs += await deletePrefix(store, `${PART_PHOTO_PREFIX}${safePhotoOwnerId(id)}/`);
  for (const id of removed.maintenance) blobs += await deletePrefix(store, `${SERVICE_PHOTO_PREFIX}maintenance/${safePhotoOwnerId(id)}/`);
  for (const id of removed.breakdowns) blobs += await deletePrefix(store, `${SERVICE_PHOTO_PREFIX}breakdowns/${safePhotoOwnerId(id)}/`);
  return {
    devices: removed.devices.length,
    parts: removed.parts.length,
    maintenance: removed.maintenance.length,
    breakdowns: removed.breakdowns.length,
    blobs,
  };
}

export function withoutPermanentPhotoRefs(storeName, item) {
  const restored = { ...(item || {}) };
  if (storeName === 'devices') {
    restored.devicePhotos = [];
    restored.deviceOverviewPhotoIndex = 0;
  }
  if (storeName === 'parts') restored.photo = '';
  if (storeName === 'maintenance' || storeName === 'breakdowns') restored.photos = [];
  return restored;
}
