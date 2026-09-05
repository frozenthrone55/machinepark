import { getStore } from '@netlify/blobs';
import {
  ALL_PERMISSION_KEYS,
  PERMISSION_CATALOG,
  hasPermission,
  normalizeRole,
  normalizeRoleConfig,
  sanitizeRoleId,
} from './_shared/permissions.mjs';
import {
  NO_STORE,
  STORE_NAME,
  authenticateClerk,
  jsonResponse as json,
  primaryEmailOf,
  resolveRoleAccess,
} from './_shared/server-auth.mjs';

const ROLE_CONFIG_KEY = 'role-config-v1';
const AUDIT_PREFIX = 'audit/';

async function authenticate(req, store) {
  const base = await authenticateClerk(req);
  const access = await resolveRoleAccess(store, base);
  if (!access.owner && !hasPermission(access.role, 'roles.manage', access.roleConfig)) {
    throw Object.assign(new Error('Deze rol mag rollen en rechten niet beheren.'), { status: 403 });
  }
  return {
    ...access,
    configEntry: access.roleConfigEtag
      ? { etag: access.roleConfigEtag, data: access.roleConfig }
      : null,
    config: access.roleConfig,
  };
}

async function roleUsageCount(clerk, roleId, config) {
  const pageSize = 100;
  let offset = 0;
  let count = 0;
  while (true) {
    const result = await clerk.users.getUserList({ limit: pageSize, offset, orderBy: '-created_at' });
    const users = result.data || [];
    count += users.filter((user) => normalizeRole(user?.publicMetadata?.role, { config }) === roleId).length;
    offset += users.length;
    const totalCount = Number(result.totalCount);
    if (users.length < pageSize || (Number.isFinite(totalCount) && offset >= totalCount)) return count;
  }
}

async function writeAudit(store, auth, action, label, fields = []) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id, at, userId: auth.sub, userEmail: email,
      userName: [auth.user.firstName, auth.user.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: 1,
      changes: [{ entityType: 'Rollenbeheer', entityId: label, entityLabel: label, action, fields }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('rollenbeheer audit', error);
  }
}

async function saveConfig(store, previousEntry, config, expectedEtag) {
  const metadata = { updatedAt: new Date().toISOString() };
  const previousEtag = previousEntry?.etag || null;
  const options = previousEtag
    ? { onlyIfMatch: expectedEtag || previousEtag, metadata }
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
        etag: auth.roleConfigEtag || null,
        ownerProtected: true,
      }, 200, auth.roleConfigEtag ? { etag: auth.roleConfigEtag } : {});
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

        const saved = await saveConfig(store, { etag: auth.roleConfigEtag }, { version: 1, roles }, body?.etag || null);
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

        const inUseCount = await roleUsageCount(auth.clerk, roleId, current);
        if (inUseCount) return json({ error: `Deze rol is nog toegewezen aan ${inUseCount} gebruiker(s). Wijs eerst een andere rol toe.` }, 409);

        const roles = current.roles.filter((role) => role.id !== roleId);
        const saved = await saveConfig(store, { etag: auth.roleConfigEtag }, { version: 1, roles }, body?.etag || null);
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
