const DEVICE_PHOTO_PREFIX = 'device-photos/';
const PART_PHOTO_PREFIX = 'part-photos/';

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
  const oldDevices = idsOf(before?.devices);
  const newDevices = idsOf(after?.devices);
  const oldParts = idsOf(before?.parts);
  const newParts = idsOf(after?.parts);
  return {
    devices: [...oldDevices].filter((id) => !newDevices.has(id)),
    parts: [...oldParts].filter((id) => !newParts.has(id)),
  };
}

export async function cleanupRemovedEntityPhotos(store, before, after) {
  if (!before || !after) return { devices: 0, parts: 0, blobs: 0 };
  const removed = removedPhotoOwners(before, after);
  let blobs = 0;
  for (const id of removed.devices) blobs += await deletePrefix(store, `${DEVICE_PHOTO_PREFIX}${safePhotoOwnerId(id)}/`);
  for (const id of removed.parts) blobs += await deletePrefix(store, `${PART_PHOTO_PREFIX}${safePhotoOwnerId(id)}/`);
  return { devices: removed.devices.length, parts: removed.parts.length, blobs };
}

export function withoutPermanentPhotoRefs(storeName, item) {
  const restored = { ...(item || {}) };
  if (storeName === 'devices') {
    restored.devicePhotos = [];
    restored.deviceOverviewPhotoIndex = 0;
  }
  if (storeName === 'parts') restored.photo = '';
  return restored;
}
