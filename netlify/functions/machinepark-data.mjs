import { getStore } from '@netlify/blobs';
import { verifyToken } from '@clerk/backend';

const STORE_NAME = 'machinepark-central';
const STATE_KEY = 'state-v1';
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
    return verified;
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

      data.updatedAt = new Date().toISOString();
      data.updatedBy = auth.sub;

      const metadata = { updatedAt: data.updatedAt, updatedBy: auth.sub };
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

      const current = await store.getMetadata(STATE_KEY, { consistency: 'strong' });
      return json({ ok: true, etag: current?.etag || null, updatedAt: data.updatedAt });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, PUT, OPTIONS' });
  } catch (error) {
    console.error('machinepark-data', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
