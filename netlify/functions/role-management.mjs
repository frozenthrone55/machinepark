import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';
import {
  ALL_PERMISSION_KEYS,
  PERMISSION_CATALOG,
  ROLE_CONFIG_KEY,
  defaultRoleConfig,
  hasPermission,
  normalizeRole,
  normalizeRoleConfig,
  roleLabel,
  sanitizeRoleId,
} from './_shared/permissions.mjs';

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

function primaryEmailOf(user) {
  const primary = (user?.emailAddresses || []).find((x) => x.id === user?.primaryEmailAddressId);
  return String(primary?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
}

async function getRoleConfig(store) {
  const entry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return { entry, config: normalizeRoleConfig(entry?.data || defaultRoleConfig()) };
}

async function authenticate(req, store) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  const authorization = req.headers.get('authorization') || '';
  const token = authorization.startsWith('Bearer ') ? authorization.slice(7).trim() : '';
  if (!token) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });

  let verified;
  try { verified = await verifyToken(token, { secretKey }); }
  catch { throw Object.assign(new Error('Clerk-sessie kon niet worden geverifieerd.'), { status: 401 }); }
  if (!verified?.sub) throw Object.assign(new Error('Aanmelding vereist.'), { status: 401 });
  const origin = req.headers.get('origin');
  if (origin && verified.azp && verified.azp !== origin) throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });

  const clerk = createClerkClient({ secretKey });
  const user = await clerk.users.getUser(verified.sub);
  const owner = emailsOf(user).includes(ADMIN_EMAIL);
  const { entry, config } = await getRoleConfig(store);
  const role = normalizeRole(user?.publicMetadata?.role, { owner, config });
  if (!owner && !hasPermission(role, 'roles.manage', config)) {
    throw Object.assign(new Error('Deze rol mag rollen en rechten niet beheren.'), { status: 403 });
  }
  return { clerk, user, owner, role, verified, configEntry: entry, config };
}

async function writeAudit(store, auth, action, label, fields = []) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.verified.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id, at, userId: auth.verified.sub, userEmail: email,
      userName: [auth.user.firstName, auth.user.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: 1,
      changes: [{ entityType: 'Rollenbeheer', entityId: label, entityLabel: label, action, fields }],
      truncated: false,
    }, { metadata: { at, userId: auth.verified.sub, userEmail: email } });
  } catch (error) {
    console.error('rollenbeheer audit', error);
  }
}

async function saveConfig(store, previousEntry, config, expectedEtag) {
  const metadata = { updatedAt: new Date().toISOString() };
  const options = previousEntry
    ? { onlyIfMatch: expectedEtag || previousEntry.etag, metadata }
    : { onlyIfNew: true, metadata };
  const result = await store.setJSON(ROLE_CONFIG_KEY, normalizeRoleConfig(config), options);
  if (!result.modified) {
    const latest = await store.getMetadata(ROLE_CONFIG_KEY, { consistency: 'strong' });
    throw Object.assign(new Error('De rollen zijn intussen door iemand anders gewijzigd. Vernieuw en probeer opnieuw.'), { status: 409, etag: latest?.etag || null });
  }
  return store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
}

function publicConfig(config) {
  return normalizeRoleConfig(config).roles.map((role) => ({
    id: role.id,
    label: role.label,
    builtIn: Boolean(role.builtIn),
    permissions: { ...role.permissions },
  }));
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });

  try {
    const auth = await authenticate(req, store);

    if (req.method === 'GET') {
      return json({
        roles: publicConfig(auth.config),
        permissionCatalog: PERMISSION_CATALOG,
        etag: auth.configEntry?.etag || null,
        ownerProtected: true,
      }, 200, auth.configEntry?.etag ? { etag: auth.configEntry.etag } : {});
    }

    if (req.method === 'POST') {
      const body = await req.json().catch(() => ({}));
      const action = String(body?.action || 'save-role');
      const current = normalizeRoleConfig(auth.config);

      if (action === 'save-role') {
        const incoming = body?.role || {};
        const requestedId = sanitizeRoleId(incoming.id || incoming.label);
        const label = String(incoming.label || '').trim().slice(0, 80);
        if (!requestedId || !label) return json({ error: 'Vul een geldige rolnaam in.' }, 400);

        const index = current.roles.findIndex((role) => role.id === requestedId);
        const existing = index >= 0 ? current.roles[index] : null;
        if (!existing && current.roles.length >= 30) return json({ error: 'Maximaal 30 rollen toegestaan.' }, 400);

        const permissions = Object.fromEntries(ALL_PERMISSION_KEYS.map((key) => [key, Boolean(incoming?.permissions?.[key])]));
        const nextRole = {
          id: requestedId,
          label: existing?.builtIn ? existing.label : label,
          builtIn: Boolean(existing?.builtIn),
          permissions,
        };
        const roles = [...current.roles];
        if (index >= 0) roles[index] = nextRole;
        else roles.push(nextRole);

        const saved = await saveConfig(store, auth.configEntry, { version: 1, roles }, body?.etag || null);
        await writeAudit(store, auth, existing ? 'aangepast' : 'toegevoegd', nextRole.label, [
          { field: 'Rol', before: existing?.label || '—', after: nextRole.label },
          { field: 'Toegestane handelingen', before: existing ? String(Object.values(existing.permissions).filter(Boolean).length) : '0', after: String(Object.values(nextRole.permissions).filter(Boolean).length) },
        ]);
        return json({ ok: true, roles: publicConfig(saved.data), etag: saved.etag || null });
      }

      if (action === 'delete-role') {
        const roleId = sanitizeRoleId(body?.roleId);
        const target = current.roles.find((role) => role.id === roleId);
        if (!target) return json({ error: 'Rol niet gevonden.' }, 404);
        if (target.builtIn) return json({ error: 'Een standaardrol kan niet worden verwijderd; de rechten ervan kunnen wel worden aangepast.' }, 400);

        const users = await auth.clerk.users.getUserList({ limit: 100, orderBy: '-created_at' });
        const inUse = (users.data || []).filter((user) => normalizeRole(user?.publicMetadata?.role, { config: current }) === roleId);
        if (inUse.length) return json({ error: `Deze rol is nog toegewezen aan ${inUse.length} gebruiker(s). Wijs eerst een andere rol toe.` }, 409);

        const roles = current.roles.filter((role) => role.id !== roleId);
        const saved = await saveConfig(store, auth.configEntry, { version: 1, roles }, body?.etag || null);
        await writeAudit(store, auth, 'verwijderd', target.label, [{ field: 'Rol', before: target.label, after: '—' }]);
        return json({ ok: true, roles: publicConfig(saved.data), etag: saved.etag || null });
      }

      return json({ error: 'Onbekende rollenactie.' }, 400);
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, OPTIONS' });
  } catch (error) {
    console.error('role-management', error);
    return json({ error: error?.message || 'Rollenbeheer mislukt.', etag: error?.etag || null }, error?.status || 500);
  }
};
