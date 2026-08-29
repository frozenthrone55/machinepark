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
const PHOTO_PREFIX = 'device-photos/';
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

async function canManageDevicePhotos(store, auth) {
  const roleEntry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  const roleConfig = normalizeRoleConfig(roleEntry?.data || defaultRoleConfig());
  const role = normalizeRole(auth.rawRole, { owner: auth.owner, config: roleConfig });
  const permissions = permissionsForRole(role, roleConfig, { owner: auth.owner });
  return Boolean(auth.owner || permissions['devices.edit'] || permissions['devices.add']);
}

function safeDeviceId(value) {
  return String(value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 100);
}

function refForKey(key) {
  return `/.netlify/functions/device-photos?key=${encodeURIComponent(key)}`;
}

function keyFromRef(value) {
  const text = String(value || '');
  if (!text.startsWith('/.netlify/functions/device-photos?key=')) return '';
  try {
    const key = decodeURIComponent(text.slice('/.netlify/functions/device-photos?key='.length));
    return key.startsWith(PHOTO_PREFIX) ? key : '';
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

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });
  try {
    if (req.method === 'GET') {
      const key = new URL(req.url).searchParams.get('key') || '';
      if (!key.startsWith(PHOTO_PREFIX)) return new Response('Ongeldige fotoreferentie.', { status: 400, headers: NO_STORE });
      const entry = await store.getWithMetadata(key, { type: 'arrayBuffer', consistency: 'strong' });
      if (!entry?.data) return new Response('Foto niet gevonden.', { status: 404, headers: NO_STORE });
      return new Response(entry.data, {
        status: 200,
        headers: {
          'content-type': entry.metadata?.contentType || 'image/jpeg',
          'cache-control': 'private, max-age=86400',
          'x-content-type-options': 'nosniff',
        },
      });
    }

    if (req.method === 'POST') {
      const auth = await authenticate(req);
      if (!(await canManageDevicePhotos(store, auth))) return json({ error: 'Deze rol mag toestelfoto’s niet wijzigen.' }, 403);
      const body = await req.json();
      const deviceId = safeDeviceId(body?.deviceId);
      const photos = Array.isArray(body?.photos) ? body.photos : [];
      if (!deviceId) return json({ error: 'Ongeldig toestel.' }, 400);
      if (photos.length > 5) return json({ error: 'Een toestel kan maximaal 5 foto’s bevatten.' }, 400);

      const prefix = `${PHOTO_PREFIX}${deviceId}/`;
      const refs = [];
      const keepKeys = new Set();
      let totalBytes = 0;

      for (const photo of photos) {
        const existingKey = keyFromRef(photo);
        if (existingKey) {
          if (!existingKey.startsWith(prefix)) return json({ error: 'Een fotoreferentie hoort niet bij dit toestel.' }, 400);
          keepKeys.add(existingKey);
          refs.push(refForKey(existingKey));
          continue;
        }
        const parsed = parseDataImage(photo);
        if (!parsed) return json({ error: 'Een toestelfoto bevat ongeldige gegevens.' }, 400);
        if (parsed.bytes.length > 1_200_000) return json({ error: 'Een toestelfoto is te groot. Kies een kleinere foto.' }, 413);
        totalBytes += parsed.bytes.length;
        if (totalBytes > 4_000_000) return json({ error: 'De geselecteerde toestelfoto’s zijn samen te groot.' }, 413);
        const key = `${prefix}${crypto.randomUUID()}`;
        await store.set(key, new Blob([parsed.bytes], { type: parsed.contentType }), {
          metadata: { contentType: parsed.contentType, deviceId, uploadedAt: new Date().toISOString(), uploadedBy: auth.sub },
        });
        keepKeys.add(key);
        refs.push(refForKey(key));
      }

      const listed = await store.list({ prefix });
      await Promise.all((listed.blobs || []).filter((item) => !keepKeys.has(item.key)).map((item) => store.delete(item.key)));
      return json({ ok: true, photos: refs });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405);
  } catch (error) {
    console.error('device-photos', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
