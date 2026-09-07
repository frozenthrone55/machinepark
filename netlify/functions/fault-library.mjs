import { getStore } from '@netlify/blobs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  primaryEmailOf,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const CONFIG_KEY = 'fault-library-v1';
const AUDIT_PREFIX = 'audit/';
const MAX_FAULTS = 5000;
const LATTIZ_CLEANUP_KEY = 'migration/fault-lattiz-cleanup-keep-00005-v1';

function cleanId(value, fallback = '') {
  const raw = String(value || fallback || '').trim();
  const id = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 90);
  return id || `fault-${crypto.randomUUID()}`;
}

function cleanText(value, max = 500) {
  return String(value || '').trim().slice(0, max);
}

function cleanLines(value, maxItems = 30, maxLength = 500) {
  const input = Array.isArray(value) ? value : String(value || '').split(/\r?\n/);
  return input
    .map((item) => cleanText(item, maxLength))
    .filter(Boolean)
    .slice(0, maxItems);
}

function normalizeScope(brand, model) {
  if (brand && model) return 'model';
  if (brand) return 'brand';
  return 'general';
}

function sanitizeFault(fault, existing = null) {
  const name = cleanText(fault?.name, 160);
  if (!name) throw Object.assign(new Error('Geef de storing een naam of korte omschrijving.'), { status: 400 });
  const brand = cleanText(fault?.brand, 100);
  const model = brand ? cleanText(fault?.model, 140) : '';
  const now = new Date().toISOString();
  return {
    id: cleanId(fault?.id, existing?.id || `${brand}-${model}-${fault?.code || ''}-${name}`),
    code: cleanText(fault?.code, 80),
    name,
    category: cleanText(fault?.category, 100),
    brand,
    model,
    scope: normalizeScope(brand, model),
    description: cleanText(fault?.description, 1600),
    symptoms: cleanLines(fault?.symptoms, 30, 500),
    causes: cleanLines(fault?.causes, 30, 500),
    solutions: cleanLines(fault?.solutions, 40, 800),
    notes: cleanText(fault?.notes, 2000),
    active: fault?.active !== false,
    version: existing ? Math.max(1, Number(existing.version || 1)) + 1 : Math.max(1, Number(fault?.version || 1)),
    createdAt: existing?.createdAt || cleanText(fault?.createdAt, 80) || now,
    updatedAt: now,
  };
}

function normalizeConfig(data) {
  const seen = new Set();
  const faults = [];
  for (const item of (Array.isArray(data?.faults) ? data.faults : []).slice(0, MAX_FAULTS)) {
    try {
      const normalized = sanitizeFault(item, item);
      if (seen.has(normalized.id)) continue;
      seen.add(normalized.id);
      faults.push({ ...normalized, version: Math.max(1, Number(item?.version || 1)), createdAt: cleanText(item?.createdAt, 80) || normalized.createdAt, updatedAt: cleanText(item?.updatedAt, 80) || normalized.updatedAt });
    } catch {
      // Skip malformed historical entries rather than breaking the complete library.
    }
  }
  return { version: 1, faults };
}

async function readConfig(store) {
  const entry = await store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return { entry, config: normalizeConfig(entry?.data || { version: 1, faults: [] }) };
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
    throw Object.assign(new Error('De storingsbibliotheek is intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.'), {
      status: 409,
      etag: latest?.etag || null,
    });
  }
  return store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
}

function scopeLabel(fault) {
  if (fault?.brand && fault?.model) return `${fault.brand} · ${fault.model}`;
  if (fault?.brand) return `${fault.brand} · alle modellen`;
  return 'Algemeen · alle merken';
}

async function writeAudit(store, auth, action, fault, before = null) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    const current = fault || before || {};
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: 1,
      changes: [{
        entityType: 'Storingen',
        entityId: current.id || '',
        entityLabel: [current.code, current.name].filter(Boolean).join(' — ') || 'Storing',
        action,
        fields: [
          { field: 'Storing', before: before ? [before.code, before.name].filter(Boolean).join(' — ') : '—', after: fault ? [fault.code, fault.name].filter(Boolean).join(' — ') : '—' },
          { field: 'Toepassing', before: before ? scopeLabel(before) : '—', after: fault ? scopeLabel(fault) : '—' },
          { field: 'Oplossingen', before: before ? String(before.solutions?.length || 0) : '—', after: fault ? String(fault.solutions?.length || 0) : '—' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('fault library audit', error);
  }
}

async function writeLattizCleanupAudit(store, auth, removed, kept) {
  if (!removed.length) return;
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    const changes = removed.slice(0, 200).map((fault) => ({
      entityType: 'Storingen',
      entityId: fault.id || '',
      entityLabel: [fault.code, fault.name].filter(Boolean).join(' — ') || 'Lattiz-storing',
      action: 'verwijderd via Lattiz-opschoning',
      fields: [
        { field: 'Storing', before: [fault.code, fault.name].filter(Boolean).join(' — ') || '—', after: '—' },
        { field: 'Toepassing', before: scopeLabel(fault), after: '—' },
      ],
    }));
    changes.unshift({
      entityType: 'Storingen',
      entityId: kept?.id || '',
      entityLabel: 'Lattiz opschoning',
      action: 'opschoning uitgevoerd',
      fields: [
        { field: 'Behouden', before: '—', after: kept ? `${kept.code || '00005'} — ${kept.name || 'Storing'}` : 'Geen' },
        { field: 'Verwijderd', before: String(removed.length), after: '0' },
      ],
    });
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: removed.length,
      changes,
      truncated: removed.length > 200,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('Lattiz cleanup audit', error);
  }
}

function canRead(access) {
  return Boolean(access?.owner || access?.permissions?.['view.faults']);
}

function canManage(access) {
  return Boolean(access?.owner || access?.permissions?.['faults.manage']);
}

function cleanupNorm(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function isLattizFault(fault) {
  return cleanupNorm(fault?.brand).includes('lattiz') || cleanupNorm(fault?.model).includes('lattiz');
}

function isLattizKeepCode(fault) {
  const digits = String(fault?.code || '').replace(/\D/g, '');
  return digits === '00005' || (digits !== '' && Number(digits) === 5);
}

async function applyOneTimeLattizCleanup(store, access, entry, config) {
  if (!canManage(access)) return { entry, config, cleanup: null };

  const migration = await store.get(LATTIZ_CLEANUP_KEY, { type: 'json', consistency: 'strong' }).catch(() => null);
  if (migration?.done) return { entry, config, cleanup: migration };

  const lattiz = config.faults.filter(isLattizFault);
  if (!lattiz.length) {
    const cleanup = { done: true, at: new Date().toISOString(), removedCount: 0, keptId: null, keptCode: null };
    await store.setJSON(LATTIZ_CLEANUP_KEY, cleanup, { metadata: { type: 'one-time-migration' } });
    return { entry, config, cleanup };
  }

  const keepCandidates = lattiz
    .filter(isLattizKeepCode)
    .sort((a, b) => String(b.updatedAt || b.createdAt || '').localeCompare(String(a.updatedAt || a.createdAt || '')));
  const kept = keepCandidates[0] || null;

  // Veiligheid: verwijder niets zolang de expliciet te behouden code 00005 niet gevonden is.
  if (!kept) return { entry, config, cleanup: { done: false, reason: 'Lattiz-code 00005 niet gevonden' } };

  const removed = lattiz.filter((fault) => fault.id !== kept.id);
  let nextEntry = entry;
  let nextConfig = config;

  if (removed.length) {
    try {
      nextEntry = await saveConfig(
        store,
        { version: 1, faults: config.faults.filter((fault) => !isLattizFault(fault) || fault.id === kept.id) },
        entry?.etag || null,
        entry?.etag || null,
      );
      nextConfig = normalizeConfig(nextEntry.data);
    } catch (error) {
      if (error?.status !== 409) throw error;
      const latest = await readConfig(store);
      const latestLattiz = latest.config.faults.filter(isLattizFault);
      const latestKept = latestLattiz.find((fault) => isLattizKeepCode(fault));
      if (!latestKept || latestLattiz.length > 1) throw error;
      nextEntry = latest.entry;
      nextConfig = latest.config;
    }
    await writeLattizCleanupAudit(store, access, removed, kept);
  }

  const cleanup = {
    done: true,
    at: new Date().toISOString(),
    removedCount: removed.length,
    keptId: kept.id,
    keptCode: kept.code || '00005',
  };
  await store.setJSON(LATTIZ_CLEANUP_KEY, cleanup, { metadata: { type: 'one-time-migration' } });
  return { entry: nextEntry, config: nextConfig, cleanup };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });

  try {
    const access = await resolveRoleAccess(store, await authenticateClerk(req));
    if (!canRead(access) && !canManage(access)) return json({ error: 'Deze rol heeft geen toegang tot de storingsbibliotheek.' }, 403);

    let { entry, config } = await readConfig(store);

    if (req.method === 'GET') {
      const migrated = await applyOneTimeLattizCleanup(store, access, entry, config);
      entry = migrated.entry;
      config = migrated.config;
      const etag = entry?.etag || null;
      return json({ faults: config.faults, etag, canManage: canManage(access), lattizCleanup: migrated.cleanup }, 200, etag ? { etag } : {});
    }

    const etag = entry?.etag || null;
    if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, OPTIONS' });
    if (!canManage(access)) return json({ error: 'Deze rol mag de storingsbibliotheek niet beheren.' }, 403);

    const body = await req.json().catch(() => ({}));
    const action = String(body?.action || 'save-fault');

    if (action === 'save-fault') {
      const incoming = body?.fault || {};
      const requestedId = incoming?.id ? cleanId(incoming.id) : '';
      const existing = requestedId ? config.faults.find((item) => item.id === requestedId) || null : null;
      if (!existing && config.faults.length >= MAX_FAULTS) return json({ error: `Maximaal ${MAX_FAULTS} storingen toegestaan.` }, 400);
      const fault = sanitizeFault({ ...incoming, id: requestedId || undefined }, existing);
      const faults = existing
        ? config.faults.map((item) => item.id === existing.id ? fault : item)
        : [...config.faults, fault];
      const saved = await saveConfig(store, { version: 1, faults }, etag, body?.etag || null);
      await writeAudit(store, access, existing ? 'aangepast' : 'toegevoegd', fault, existing);
      return json({ ok: true, faults: normalizeConfig(saved.data).faults, etag: saved.etag || null, canManage: true });
    }

    if (action === 'delete-fault') {
      const faultId = cleanId(body?.faultId);
      const existing = config.faults.find((item) => item.id === faultId);
      if (!existing) return json({ error: 'Storing niet gevonden.' }, 404);
      const faults = config.faults.filter((item) => item.id !== faultId);
      const saved = await saveConfig(store, { version: 1, faults }, etag, body?.etag || null);
      await writeAudit(store, access, 'verwijderd', null, existing);
      return json({ ok: true, faults: normalizeConfig(saved.data).faults, etag: saved.etag || null, canManage: true });
    }

    return json({ error: 'Onbekende storingsactie.' }, 400);
  } catch (error) {
    console.error('fault-library', error);
    return json({ error: error?.message || 'Storingsbibliotheek mislukt.', etag: error?.etag || null }, error?.status || 500);
  }
};
