import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';
import {
  ROLE_CONFIG_KEY,
  defaultRoleConfig,
  normalizeRole,
  normalizeRoleConfig,
  permissionsForRole,
} from './_shared/permissions.mjs';

const STORE_NAME = 'machinepark-central';
const PHOTO_PREFIX = 'part-photos/';
const THUMB_SUFFIX = '.thumb';
const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };

function json(data, status = 200) {
  return Response.json(data, { status, headers: NO_STORE });
}

async function authenticate(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });
  try {
    const verified = await verifyToken(token, { secretKey });
    if (!verified?.sub) throw new Error('Geen gebruiker in token.');
    const origin = req.headers.get('origin');
    if (origin && verified.azp && verified.azp !== origin) throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
    const clerk = createClerkClient({ secretKey });
    const user = await clerk.users.getUser(verified.sub);
    const primary = (user.emailAddresses || []).find((x) => x.id === user.primaryEmailAddressId);
    const email = String(primary?.emailAddress || user.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
    const owner = (user.emailAddresses || []).some((x) => String(x.emailAddress || '').trim().toLowerCase() === ADMIN_EMAIL);
    return { ...verified, email, owner, rawRole: user?.publicMetadata?.role || 'gebruiker' };
  } catch (error) {
    if (error?.status) throw error;
    throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 });
  }
}

async function canManagePartPhotos(store, auth) {
  const roleEntry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  const roleConfig = normalizeRoleConfig(roleEntry?.data || defaultRoleConfig());
  const role = normalizeRole(auth.rawRole, { owner: auth.owner, config: roleConfig });
  const permissions = permissionsForRole(role, roleConfig, { owner: auth.owner });
  return Boolean(auth.owner || permissions['parts.edit'] || permissions['parts.add']);
}

function safePartId(value) {
  return String(value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100);
}

function photoKey(partId) {
  return `${PHOTO_PREFIX}${partId}/photo`;
}

function thumbKey(key) {
  return `${key}${THUMB_SUFFIX}`;
}

function refForKey(key, variant = '') {
  const suffix = variant === 'thumb' ? '&variant=thumb' : '';
  return `/.netlify/functions/part-photos?key=${encodeURIComponent(key)}${suffix}`;
}

function keyFromRef(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  try {
    const url = new URL(text, 'https://machinepark.local');
    if (url.pathname !== '/.netlify/functions/part-photos') return '';
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
    metadata: { contentType: parsed.contentType, sourceKey: key, generatedAt: new Date().toISOString(), generatedBy: auth?.sub || '' },
  });
  return true;
}

async function imageResponse(store, key, variant, headOnly = false) {
  if (!key.startsWith(PHOTO_PREFIX) || key.endsWith(THUMB_SUFFIX)) return new Response('Ongeldige fotoreferentie.', { status: 400, headers: NO_STORE });
  if (variant === 'thumb') {
    const thumbnail = await store.getWithMetadata(thumbKey(key), { type: 'arrayBuffer', consistency: 'strong' });
    if (headOnly) return new Response(null, { status: thumbnail?.data ? 200 : 404, headers: { ...NO_STORE, 'x-machinepark-thumbnail': thumbnail?.data ? 'exact' : 'missing' } });
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
  if (headOnly) return new Response(null, { status: 200, headers: { ...NO_STORE, 'x-machinepark-thumbnail': variant === 'thumb' ? 'fallback' : 'full' } });
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

    if (req.method === 'POST') {
      const auth = await authenticate(req);
      const body = await req.json();
      const action = String(body?.action || 'save');
      const partId = safePartId(body?.partId);
      if (!partId) return json({ error: 'Ongeldig onderdeel.' }, 400);
      const key = photoKey(partId);

      if (action === 'thumbnail') {
        const refKey = keyFromRef(body?.photoRef);
        if (refKey !== key) return json({ error: 'De fotoreferentie hoort niet bij dit onderdeel.' }, 400);
        const original = await store.getMetadata(key, { consistency: 'strong' });
        if (!original) return json({ error: 'De originele onderdeelfoto bestaat niet meer.' }, 404);
        await storeThumbnail(store, key, body?.thumbnail, auth);
        return json({ ok: true, thumbnail: refForKey(key, 'thumb') });
      }

      if (!(await canManagePartPhotos(store, auth))) return json({ error: 'Deze rol mag onderdeelfoto’s niet wijzigen.' }, 403);
      const photo = String(body?.photo || '').trim();
      const thumbnail = String(body?.thumbnail || '').trim();
      if (!photo) {
        await Promise.all([store.delete(key), store.delete(thumbKey(key))]);
        return json({ ok: true, photo: '' });
      }

      const existingKey = keyFromRef(photo);
      if (existingKey) {
        if (existingKey !== key) return json({ error: 'De fotoreferentie hoort niet bij dit onderdeel.' }, 400);
        if (thumbnail) await storeThumbnail(store, key, thumbnail, auth);
        return json({ ok: true, photo: refForKey(key) });
      }

      const parsed = parseDataImage(photo);
      if (!parsed) return json({ error: 'De onderdeelfoto bevat ongeldige gegevens.' }, 400);
      if (parsed.bytes.length > 1_500_000) return json({ error: 'De onderdeelfoto is te groot. Kies een kleinere foto.' }, 413);
      await store.set(key, new Blob([parsed.bytes], { type: parsed.contentType }), {
        metadata: { contentType: parsed.contentType, partId, uploadedAt: new Date().toISOString(), uploadedBy: auth.sub },
      });
      if (thumbnail) await storeThumbnail(store, key, thumbnail, auth);
      return json({ ok: true, photo: refForKey(key) });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405);
  } catch (error) {
    console.error('part-photos', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
