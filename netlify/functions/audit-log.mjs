import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';

const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
const STORE_NAME = 'machinepark-central';
const AUDIT_PREFIX = 'audit/';
const NO_STORE = { 'cache-control': 'no-store, max-age=0' };

function json(data, status = 200, headers = {}) {
  return Response.json(data, { status, headers: { ...NO_STORE, ...headers } });
}

function emailsOf(user) {
  return (user?.emailAddresses || []).map((x) => String(x.emailAddress || '').trim().toLowerCase()).filter(Boolean);
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
  if (!emailsOf(currentUser).includes(ADMIN_EMAIL)) {
    throw Object.assign(new Error('Alleen de beheerder heeft toegang tot het logboek.'), { status: 403 });
  }
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });

  try {
    await authenticateAdmin(req);
    if (req.method !== 'GET') return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, OPTIONS' });

    const store = getStore({ name: STORE_NAME, consistency: 'strong' });
    const { blobs } = await store.list({ prefix: AUDIT_PREFIX });
    const selected = [...(blobs || [])].sort((a, b) => b.key.localeCompare(a.key)).slice(0, 250);

    const entries = await Promise.all(selected.map(async ({ key }) => {
      try {
        const entry = await store.getWithMetadata(key, { type: 'json', consistency: 'strong' });
        return entry?.data || null;
      } catch (error) {
        console.error('audit entry lezen', key, error);
        return null;
      }
    }));

    return json({ entries: entries.filter(Boolean) });
  } catch (error) {
    console.error('audit-log', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
