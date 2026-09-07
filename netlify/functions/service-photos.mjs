import { getStore } from '@netlify/blobs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';
import { safePhotoOwnerId } from './_shared/photo-cleanup.mjs';

const PHOTO_PREFIX = 'service-photos/';
const THUMB_SUFFIX = '.thumb';
const VALID_STORES = new Set(['maintenance', 'breakdowns']);

function safeStoreName(value) {
  const storeName = String(value || '').trim();
  return VALID_STORES.has(storeName) ? storeName : '';
}

function ownerPrefix(storeName, entityId) {
  return `${PHOTO_PREFIX}${storeName}/${safePhotoOwnerId(entityId)}/`;
}

function thumbKey(key) {
  return `${key}${THUMB_SUFFIX}`;
}

function refForKey(key, variant = '') {
  const suffix = variant === 'thumb' ? '&variant=thumb' : '';
  return `/.netlify/functions/service-photos?key=${encodeURIComponent(key)}${suffix}`;
}

function keyFromRef(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  try {
    const url = new URL(text, 'https://machinepark.local');
    if (url.pathname !== '/.netlify/functions/service-photos') return '';
    const key = decodeURIComponent(url.searchParams.get('key') || '');
    return key.startsWith(PHOTO_PREFIX) && !key.endsWith(THUMB_SUFFIX) ? key : '';
  } catch (_) {
    return '';
  }
}

function parseDataImage(value) {
  const match = /^data:(image\/[a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)$/.exec(String(value || ''));
  if (!match) return null;
  const bytes = Buffer.from(match[2].replace(/\s+/g, ''), 'base64');
  if (!bytes.length) return null;
  return { contentType: match[1], bytes };
}

async function storeThumbnail(store, key, raw, auth) {
  if (!raw) return false;
  const parsed = parseDataImage(raw);
  if (!parsed) throw Object.assign(new Error('De thumbnail bevat ongeldige afbeeldingsgegevens.'), { status: 400 });
  if (parsed.bytes.length > 180_000) throw Object.assign(new Error('De thumbnail is te groot.'), { status: 413 });
  await store.set(thumbKey(key), new Blob([parsed.bytes], { type: parsed.contentType }), {
    metadata: {
      contentType: parsed.contentType,
      sourceKey: key,
      generatedAt: new Date().toISOString(),
      generatedBy: auth?.sub || '',
    },
  });
  return true;
}

async function imageResponse(store, key, variant, headOnly = false) {
  if (!key.startsWith(PHOTO_PREFIX) || key.endsWith(THUMB_SUFFIX)) {
    return new Response('Ongeldige fotoreferentie.', { status: 400, headers: NO_STORE });
  }
  if (variant === 'thumb') {
    const thumbnail = await store.getWithMetadata(thumbKey(key), { type: 'arrayBuffer', consistency: 'strong' });
    if (headOnly) {
      return new Response(null, {
        status: thumbnail?.data ? 200 : 404,
        headers: { ...NO_STORE, 'x-machinepark-thumbnail': thumbnail?.data ? 'exact' : 'missing' },
      });
    }
    if (thumbnail?.data) {
      return new Response(thumbnail.data, {
        status: 200,
        headers: {
          'content-type': thumbnail.metadata?.contentType || 'image/jpeg',
          'cache-control': 'private, max-age=604800',
          'x-content-type-options': 'nosniff',
          'x-machinepark-thumbnail': 'exact',
        },
      });
    }
  }

  const entry = await store.getWithMetadata(key, { type: 'arrayBuffer', consistency: 'strong' });
  if (!entry?.data) return new Response('Foto niet gevonden.', { status: 404, headers: NO_STORE });
  if (headOnly) {
    return new Response(null, {
      status: 200,
      headers: { ...NO_STORE, 'x-machinepark-thumbnail': variant === 'thumb' ? 'fallback' : 'full' },
    });
  }
  return new Response(entry.data, {
    status: 200,
    headers: {
      'content-type': entry.metadata?.contentType || 'image/jpeg',
      'cache-control': 'private, max-age=86400',
      'x-content-type-options': 'nosniff',
      'x-machinepark-thumbnail': variant === 'thumb' ? 'fallback' : 'full',
    },
  });
}

async function canManageServicePhotos(store, auth, storeName) {
  const access = await resolveRoleAccess(store, auth);
  const prefix = storeName === 'maintenance' ? 'maintenance' : 'breakdowns';
  return Boolean(access.owner || access.permissions[`${prefix}.edit`] || access.permissions[`${prefix}.add`]);
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });

  try {
    if (req.method === 'GET' || req.method === 'HEAD') {
      const url = new URL(req.url);
      const key = url.searchParams.get('key') || '';
      const variant = url.searchParams.get('variant') === 'thumb' ? 'thumb' : 'full';
      return imageResponse(store, key, variant, req.method === 'HEAD');
    }

    if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405);

    const auth = await authenticateClerk(req);
    const body = await req.json();
    const action = String(body?.action || 'save');
    const storeName = safeStoreName(body?.storeName);
    const entityId = safePhotoOwnerId(body?.entityId);
    if (!storeName || !entityId) return json({ error: 'Ongeldig onderhouds- of depannagedossier.' }, 400);
    const prefix = ownerPrefix(storeName, entityId);

    if (action === 'thumbnail') {
      const key = keyFromRef(body?.photoRef);
      if (!key || !key.startsWith(prefix)) return json({ error: 'De fotoreferentie hoort niet bij dit dossier.' }, 400);
      const original = await store.getMetadata(key, { consistency: 'strong' });
      if (!original) return json({ error: 'De originele verslagfoto bestaat niet meer.' }, 404);
      await storeThumbnail(store, key, body?.thumbnail, auth);
      return json({ ok: true, thumbnail: refForKey(key, 'thumb') });
    }

    if (!(await canManageServicePhotos(store, auth, storeName))) {
      return json({ error: 'Deze rol mag verslagfoto’s niet wijzigen.' }, 403);
    }

    const photos = Array.isArray(body?.photos) ? body.photos : [];
    const thumbnails = Array.isArray(body?.thumbnails) ? body.thumbnails : [];
    if (photos.length > 5) return json({ error: 'Een onderhouds- of depannageverslag kan maximaal 5 foto’s bevatten.' }, 400);

    const refs = new Array(photos.length);
    const keepKeys = new Set();
    const writes = [];
    let totalBytes = 0;

    for (let index = 0; index < photos.length; index += 1) {
      const photo = String(photos[index] || '').trim();
      const thumbnail = String(thumbnails[index] || '').trim();
      const existingKey = keyFromRef(photo);
      if (existingKey) {
        if (!existingKey.startsWith(prefix)) return json({ error: 'Een fotoreferentie hoort niet bij dit dossier.' }, 400);
        keepKeys.add(existingKey);
        keepKeys.add(thumbKey(existingKey));
        refs[index] = refForKey(existingKey);
        if (thumbnail) writes.push(storeThumbnail(store, existingKey, thumbnail, auth));
        continue;
      }

      const parsed = parseDataImage(photo);
      if (!parsed) return json({ error: 'Een verslagfoto bevat ongeldige gegevens.' }, 400);
      if (parsed.bytes.length > 1_200_000) return json({ error: 'Een verslagfoto is te groot. Kies een kleinere foto.' }, 413);
      totalBytes += parsed.bytes.length;
      if (totalBytes > 4_000_000) return json({ error: 'De geselecteerde verslagfoto’s zijn samen te groot.' }, 413);

      const key = `${prefix}${crypto.randomUUID()}`;
      keepKeys.add(key);
      refs[index] = refForKey(key);
      writes.push(store.set(key, new Blob([parsed.bytes], { type: parsed.contentType }), {
        metadata: {
          contentType: parsed.contentType,
          storeName,
          entityId,
          uploadedAt: new Date().toISOString(),
          uploadedBy: auth.sub,
        },
      }));
      if (thumbnail) {
        keepKeys.add(thumbKey(key));
        writes.push(storeThumbnail(store, key, thumbnail, auth));
      }
    }

    await Promise.all(writes);
    const listed = await store.list({ prefix });
    await Promise.all((listed.blobs || []).filter((item) => !keepKeys.has(item.key)).map((item) => store.delete(item.key)));
    return json({ ok: true, photos: refs });
  } catch (error) {
    console.error('service-photos', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
