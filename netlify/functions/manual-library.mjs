import { getStore } from '@netlify/blobs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  primaryEmailOf,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const CONFIG_KEY = 'manual-library-v1';
const FILE_PREFIX = 'manual-files/';
const AUDIT_PREFIX = 'audit/';
const MAX_MANUALS = 1500;
const MAX_FILE_BYTES = 12_000_000;

function cleanText(value, max = 500) {
  return String(value || '').trim().slice(0, max);
}

function cleanId(value, fallback = '') {
  const raw = String(value || fallback || '').trim();
  const id = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 90);
  return id || `manual-${crypto.randomUUID()}`;
}

function safeFileKey(value) {
  const key = String(value || '').trim();
  return key.startsWith(FILE_PREFIX) && /^manual-files\/[a-zA-Z0-9._-]+$/.test(key) ? key : '';
}

function sanitizeManual(raw, existing = null) {
  const title = cleanText(raw?.title, 180);
  if (!title) throw Object.assign(new Error('Geef de handleiding een titel.'), { status: 400 });
  const fileKey = safeFileKey(raw?.fileKey || existing?.fileKey);
  if (!fileKey) throw Object.assign(new Error('Kies een geldig PDF-bestand voor deze handleiding.'), { status: 400 });
  const brand = cleanText(raw?.brand, 100);
  const model = brand ? cleanText(raw?.model, 140) : '';
  const now = new Date().toISOString();
  return {
    id: cleanId(raw?.id, existing?.id || `${brand}-${model}-${title}`),
    title,
    type: cleanText(raw?.type, 100) || 'Overig',
    brand,
    model,
    deviceId: cleanText(raw?.deviceId, 120),
    versionLabel: cleanText(raw?.versionLabel, 80),
    language: cleanText(raw?.language, 60) || 'Nederlands',
    notes: cleanText(raw?.notes, 2000),
    fileKey,
    fileName: cleanText(raw?.fileName || existing?.fileName, 220) || 'handleiding.pdf',
    fileSize: Math.max(0, Number(raw?.fileSize ?? existing?.fileSize ?? 0) || 0),
    active: raw?.active !== false,
    version: existing ? Math.max(1, Number(existing.version || 1)) + 1 : Math.max(1, Number(raw?.version || 1)),
    createdAt: existing?.createdAt || cleanText(raw?.createdAt, 80) || now,
    updatedAt: now,
  };
}

function normalizeConfig(data) {
  const manuals = [];
  const seen = new Set();
  for (const item of (Array.isArray(data?.manuals) ? data.manuals : []).slice(0, MAX_MANUALS)) {
    try {
      const normalized = sanitizeManual(item, item);
      if (seen.has(normalized.id)) continue;
      seen.add(normalized.id);
      manuals.push({
        ...normalized,
        version: Math.max(1, Number(item?.version || 1)),
        createdAt: cleanText(item?.createdAt, 80) || normalized.createdAt,
        updatedAt: cleanText(item?.updatedAt, 80) || normalized.updatedAt,
      });
    } catch {
      // Een beschadigde historische regel mag de volledige bibliotheek niet blokkeren.
    }
  }
  return { version: 1, manuals };
}

async function readConfig(store) {
  const entry = await store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return { entry, config: normalizeConfig(entry?.data || { version: 1, manuals: [] }) };
}

async function saveConfig(store, config, currentEtag, expectedEtag) {
  const normalized = normalizeConfig(config);
  const metadata = { updatedAt: new Date().toISOString() };
  const options = currentEtag
    ? { onlyIfMatch: expectedEtag || currentEtag, metadata }
    : { onlyIfNew: true, metadata };
  const result = await store.setJSON(CONFIG_KEY, normalized, options);
  if (!result.modified) {
    const latest = await store.getMetadata(CONFIG_KEY, { consistency: 'strong' });
    throw Object.assign(new Error('De handleidingenbibliotheek is intussen op een ander toestel gewijzigd. Vernieuw en probeer opnieuw.'), {
      status: 409,
      etag: latest?.etag || null,
    });
  }
  return store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
}

function canRead(access) {
  return Boolean(
    access?.owner ||
    access?.permissions?.['view.devices'] ||
    access?.permissions?.['view.breakdowns'] ||
    access?.permissions?.['view.settings']
  );
}

function canManage(access) {
  return Boolean(access?.owner || access?.permissions?.['view.settings']);
}

function scopeLabel(manual) {
  if (manual?.deviceId) return `Specifiek toestel · ${manual.deviceId}`;
  if (manual?.brand && manual?.model) return `${manual.brand} · ${manual.model}`;
  if (manual?.brand) return `${manual.brand} · alle modellen`;
  return 'Algemeen · alle toestellen';
}

async function writeAudit(store, access, action, manual, before = null) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(access.user) || access.sub;
    const current = manual || before || {};
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: access.sub,
      userEmail: email,
      userName: [access.user?.firstName, access.user?.lastName].filter(Boolean).join(' '),
      userRole: access.role,
      changeCount: 1,
      changes: [{
        entityType: 'Handleidingen',
        entityId: current.id || '',
        entityLabel: current.title || current.fileName || 'Handleiding',
        action,
        fields: [
          { field: 'Titel', before: before?.title || '—', after: manual?.title || '—' },
          { field: 'Type', before: before?.type || '—', after: manual?.type || '—' },
          { field: 'Toepassing', before: before ? scopeLabel(before) : '—', after: manual ? scopeLabel(manual) : '—' },
          { field: 'PDF', before: before?.fileName || '—', after: manual?.fileName || '—' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: access.sub, userEmail: email } });
  } catch (error) {
    console.error('manual library audit', error);
  }
}

async function pdfResponse(store, config, key) {
  const manual = config.manuals.find((item) => item.fileKey === key && item.active !== false);
  if (!manual) return new Response('Handleiding niet gevonden.', { status: 404, headers: NO_STORE });
  const entry = await store.getWithMetadata(key, { type: 'arrayBuffer', consistency: 'strong' });
  if (!entry?.data) return new Response('PDF-bestand niet gevonden.', { status: 404, headers: NO_STORE });
  const safeName = String(manual.fileName || 'handleiding.pdf').replace(/[\r\n"]/g, '_');
  return new Response(entry.data, {
    status: 200,
    headers: {
      'content-type': 'application/pdf',
      'content-disposition': `inline; filename="${safeName}"`,
      'cache-control': 'private, no-store, max-age=0',
      'x-content-type-options': 'nosniff',
    },
  });
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });
  try {
    const auth = await authenticateClerk(req);
    const access = await resolveRoleAccess(store, auth);
    const url = new URL(req.url);

    if (req.method === 'GET') {
      if (!canRead(access)) return json({ error: 'Deze rol mag geen handleidingen bekijken.' }, 403);
      const { entry, config } = await readConfig(store);
      const fileKey = safeFileKey(url.searchParams.get('file'));
      if (fileKey) return pdfResponse(store, config, fileKey);
      const etag = entry?.etag || null;
      const clientEtag = req.headers.get('x-machinepark-if-none-match') || '';
      if (etag && clientEtag && clientEtag === etag) {
        return json({ unchanged: true, etag, canManage: canManage(access) });
      }
      return json({ manuals: config.manuals, etag, canManage: canManage(access) });
    }

    if (req.method === 'PUT') {
      if (!canManage(access)) return json({ error: 'Alleen een beheerder kan handleidingen uploaden.' }, 403);
      if (url.searchParams.get('action') !== 'upload') return json({ error: 'Ongeldige uploadactie.' }, 400);
      const fileName = cleanText(url.searchParams.get('fileName'), 220) || 'handleiding.pdf';
      if (!fileName.toLowerCase().endsWith('.pdf')) return json({ error: 'Alleen PDF-handleidingen zijn toegestaan.' }, 400);
      const bytes = Buffer.from(await req.arrayBuffer());
      if (!bytes.length) return json({ error: 'Het PDF-bestand is leeg.' }, 400);
      if (bytes.length > MAX_FILE_BYTES) return json({ error: 'De PDF is groter dan 12 MB.' }, 413);
      if (bytes.subarray(0, 5).toString('ascii') !== '%PDF-') return json({ error: 'Het gekozen bestand is geen geldige PDF.' }, 400);
      const key = `${FILE_PREFIX}${crypto.randomUUID()}.pdf`;
      await store.set(key, new Blob([bytes], { type: 'application/pdf' }), {
        metadata: {
          contentType: 'application/pdf',
          fileName,
          size: bytes.length,
          uploadedAt: new Date().toISOString(),
          uploadedBy: access.sub,
        },
      });
      return json({ ok: true, fileKey: key, fileName, fileSize: bytes.length });
    }

    if (req.method === 'POST') {
      if (!canManage(access)) return json({ error: 'Alleen een beheerder kan handleidingen wijzigen.' }, 403);
      const body = await req.json();
      const action = String(body?.action || 'save-manual');
      const { entry, config } = await readConfig(store);
      const etag = entry?.etag || null;

      if (action === 'save-manual') {
        const requestedId = cleanText(body?.manual?.id, 100);
        const index = requestedId ? config.manuals.findIndex((item) => item.id === requestedId) : -1;
        const existing = index >= 0 ? config.manuals[index] : null;
        const manual = sanitizeManual(body?.manual || {}, existing);
        const fileMeta = await store.getMetadata(manual.fileKey, { consistency: 'strong' });
        if (!fileMeta) return json({ error: 'Het geüploade PDF-bestand bestaat niet meer. Upload het opnieuw.' }, 400);
        const manuals = [...config.manuals];
        if (existing) manuals[index] = manual;
        else {
          if (manuals.length >= MAX_MANUALS) return json({ error: `Maximaal ${MAX_MANUALS} handleidingen toegestaan.` }, 400);
          manuals.push(manual);
        }
        const saved = await saveConfig(store, { version: 1, manuals }, etag, body?.etag || null);
        if (existing?.fileKey && existing.fileKey !== manual.fileKey) await store.delete(existing.fileKey).catch(() => {});
        await writeAudit(store, access, existing ? 'bijgewerkt' : 'toegevoegd', manual, existing);
        return json({ ok: true, manual, manuals: normalizeConfig(saved.data).manuals, etag: saved.etag || null });
      }

      if (action === 'delete-manual') {
        const id = cleanText(body?.id, 100);
        const existing = config.manuals.find((item) => item.id === id);
        if (!existing) return json({ error: 'Handleiding niet gevonden.' }, 404);
        const saved = await saveConfig(store, { version: 1, manuals: config.manuals.filter((item) => item.id !== id) }, etag, body?.etag || null);
        if (existing.fileKey) await store.delete(existing.fileKey).catch(() => {});
        await writeAudit(store, access, 'verwijderd', null, existing);
        return json({ ok: true, manuals: normalizeConfig(saved.data).manuals, etag: saved.etag || null });
      }

      return json({ error: 'Onbekende handleidingenactie.' }, 400);
    }

    return json({ error: 'Methode niet toegestaan.' }, 405);
  } catch (error) {
    console.error('manual-library', error);
    return json({ error: error?.message || 'Onbekende serverfout.', etag: error?.etag || null }, error?.status || 500);
  }
};
