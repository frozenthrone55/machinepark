import { getStore } from '@netlify/blobs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  primaryEmailOf,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const CONFIG_KEY = 'work-order-templates-v1';
const AUDIT_PREFIX = 'audit/';
const FIELD_TYPES = new Set(['text', 'textarea', 'number', 'checkbox', 'select', 'date']);

function cleanList(value, maxItems = 20) {
  const input = Array.isArray(value) ? value : String(value || '').split(',');
  return [...new Set(input.map((item) => String(item || '').trim()).filter(Boolean))].slice(0, maxItems);
}

function cleanId(value, fallback = '') {
  const id = String(value || fallback || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
  return id || `wo-${crypto.randomUUID()}`;
}

function sanitizeField(field, index = 0) {
  const label = String(field?.label || '').trim().slice(0, 120);
  if (!label) return null;
  const type = FIELD_TYPES.has(String(field?.type || 'text')) ? String(field.type) : 'text';
  const options = type === 'select' ? cleanList(field?.options, 40).map((item) => item.slice(0, 100)) : [];
  return {
    id: cleanId(field?.id, `veld-${index + 1}`),
    label,
    type,
    required: Boolean(field?.required),
    options,
  };
}

function sanitizeTemplate(template, existing = null) {
  const name = String(template?.name || '').trim().slice(0, 120);
  if (!name) throw Object.assign(new Error('Geef de werkbon een naam.'), { status: 400 });
  const fields = (Array.isArray(template?.fields) ? template.fields : [])
    .slice(0, 60)
    .map(sanitizeField)
    .filter(Boolean);
  if (!fields.length) throw Object.assign(new Error('Voeg minstens één veld aan de werkbon toe.'), { status: 400 });
  const now = new Date().toISOString();
  return {
    id: cleanId(template?.id, existing?.id || name),
    name,
    description: String(template?.description || '').trim().slice(0, 500),
    active: template?.active !== false,
    brands: cleanList(template?.brands, 20).map((item) => item.slice(0, 80)),
    models: cleanList(template?.models, 30).map((item) => item.slice(0, 120)),
    version: existing ? Math.max(1, Number(existing.version || 1)) + 1 : 1,
    fields,
    createdAt: existing?.createdAt || now,
    updatedAt: now,
  };
}

function normalizeConfig(data) {
  const templates = (Array.isArray(data?.templates) ? data.templates : [])
    .slice(0, 60)
    .map((template) => {
      try {
        const fields = (Array.isArray(template?.fields) ? template.fields : []).map(sanitizeField).filter(Boolean);
        return {
          id: cleanId(template?.id, template?.name),
          name: String(template?.name || 'Werkbon').trim().slice(0, 120) || 'Werkbon',
          description: String(template?.description || '').trim().slice(0, 500),
          active: template?.active !== false,
          brands: cleanList(template?.brands, 20).map((item) => item.slice(0, 80)),
          models: cleanList(template?.models, 30).map((item) => item.slice(0, 120)),
          version: Math.max(1, Number(template?.version || 1)),
          fields,
          createdAt: String(template?.createdAt || ''),
          updatedAt: String(template?.updatedAt || ''),
        };
      } catch {
        return null;
      }
    })
    .filter((template) => template && template.fields.length);
  return { version: 1, templates };
}

async function readConfig(store) {
  const entry = await store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return { entry, config: normalizeConfig(entry?.data || { version: 1, templates: [] }) };
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
    throw Object.assign(new Error('De werkbonnen zijn intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.'), {
      status: 409,
      etag: latest?.etag || null,
    });
  }
  return store.getWithMetadata(CONFIG_KEY, { type: 'json', consistency: 'strong' });
}

async function writeAudit(store, auth, action, template, before = null) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: 1,
      changes: [{
        entityType: 'Werkbonnen',
        entityId: template?.id || before?.id || '',
        entityLabel: template?.name || before?.name || 'Werkbon',
        action,
        fields: [
          { field: 'Werkbon', before: before?.name || '—', after: template?.name || '—' },
          { field: 'Versie', before: before ? String(before.version || 1) : '—', after: template ? String(template.version || 1) : '—' },
          { field: 'Velden', before: before ? String(before.fields?.length || 0) : '—', after: template ? String(template.fields?.length || 0) : '—' },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('werkbon audit', error);
  }
}

function canRead(access) {
  return Boolean(
    access?.owner ||
    access?.permissions?.['view.maintenance'] ||
    access?.permissions?.['maintenance.add'] ||
    access?.permissions?.['maintenance.edit']
  );
}

function canManage(access) {
  return Boolean(access?.owner || access?.role === 'beheerder');
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });

  try {
    const access = await resolveRoleAccess(store, await authenticateClerk(req));
    if (!canRead(access) && !canManage(access)) {
      return json({ error: 'Deze rol heeft geen toegang tot werkbonnen.' }, 403);
    }

    const { entry, config } = await readConfig(store);
    const etag = entry?.etag || null;

    if (req.method === 'GET') {
      return json({ templates: config.templates, etag, canManage: canManage(access) }, 200, etag ? { etag } : {});
    }

    if (req.method !== 'POST') return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, OPTIONS' });
    if (!canManage(access)) return json({ error: 'Alleen een beheerder kan werkbonnen configureren.' }, 403);

    const body = await req.json().catch(() => ({}));
    const action = String(body?.action || 'save-template');

    if (action === 'save-template') {
      const incoming = body?.template || {};
      const requestedId = cleanId(incoming?.id, incoming?.name);
      const existing = config.templates.find((item) => item.id === requestedId) || null;
      if (!existing && config.templates.length >= 60) return json({ error: 'Maximaal 60 werkbontemplates toegestaan.' }, 400);
      const template = sanitizeTemplate({ ...incoming, id: requestedId }, existing);
      const templates = existing
        ? config.templates.map((item) => item.id === existing.id ? template : item)
        : [...config.templates, template];
      const saved = await saveConfig(store, { version: 1, templates }, etag, body?.etag || null);
      await writeAudit(store, access, existing ? 'aangepast' : 'toegevoegd', template, existing);
      return json({ ok: true, templates: normalizeConfig(saved.data).templates, etag: saved.etag || null });
    }

    if (action === 'delete-template') {
      const templateId = cleanId(body?.templateId);
      const existing = config.templates.find((item) => item.id === templateId);
      if (!existing) return json({ error: 'Werkbon niet gevonden.' }, 404);
      const templates = config.templates.filter((item) => item.id !== templateId);
      const saved = await saveConfig(store, { version: 1, templates }, etag, body?.etag || null);
      await writeAudit(store, access, 'verwijderd', null, existing);
      return json({ ok: true, templates: normalizeConfig(saved.data).templates, etag: saved.etag || null });
    }

    return json({ error: 'Onbekende werkbonactie.' }, 400);
  } catch (error) {
    console.error('work-order-templates', error);
    return json({ error: error?.message || 'Werkbonbeheer mislukt.', etag: error?.etag || null }, error?.status || 500);
  }
};
