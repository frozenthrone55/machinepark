import { getStore } from '@netlify/blobs';
import { createClerkClient, verifyToken } from '@clerk/backend';
import {
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

function isOwnerUser(user) { return emailsOf(user).includes(ADMIN_EMAIL); }

async function loadRoleConfig(store) {
  const entry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return normalizeRoleConfig(entry?.data || defaultRoleConfig());
}

function roleOf(user, config) {
  return normalizeRole(user?.publicMetadata?.role, { owner: isOwnerUser(user), config });
}

async function authenticateManager(req, store) {
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
  if (origin && verified.azp && verified.azp !== origin) {
    throw Object.assign(new Error('Deze sessie hoort niet bij deze website.'), { status: 403 });
  }

  const clerk = createClerkClient({ secretKey });
  const currentUser = await clerk.users.getUser(verified.sub);
  const config = await loadRoleConfig(store);
  const owner = isOwnerUser(currentUser);
  const role = roleOf(currentUser, config);
  if (!owner && !hasPermission(role, 'users.manage', config)) {
    throw Object.assign(new Error('Deze rol mag gebruikers niet beheren.'), { status: 403 });
  }
  return { clerk, currentUser, verified, config, owner, role };
}

async function writeAdminAudit(store, auth, action, label, fields = []) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.currentUser) || auth.verified.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id, at,
      userId: auth.verified.sub,
      userEmail: email,
      userName: [auth.currentUser.firstName, auth.currentUser.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: 1,
      changes: [{ entityType: 'Gebruikersbeheer', entityId: label, entityLabel: label, action, fields }],
      truncated: false,
    }, { metadata: { at, userId: auth.verified.sub, userEmail: email } });
  } catch (error) {
    console.error('gebruikersbeheer audit', error);
  }
}

function serializeUser(user, config) {
  const role = roleOf(user, config);
  return {
    id: user.id,
    email: primaryEmailOf(user),
    firstName: user.firstName || '',
    lastName: user.lastName || '',
    fullName: [user.firstName, user.lastName].filter(Boolean).join(' '),
    role,
    roleLabel: roleLabel(role, config),
    isOwner: isOwnerUser(user),
    imageUrl: user.imageUrl || '',
    lastSignInAt: user.lastSignInAt || null,
    createdAt: user.createdAt || null,
    banned: Boolean(user.banned),
    locked: Boolean(user.locked),
  };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });
  const store = getStore({ name: STORE_NAME, consistency: 'strong' });

  try {
    const auth = await authenticateManager(req, store);
    const { clerk, currentUser, config } = auth;
    const availableRoles = config.roles.map((role) => ({ value: role.id, label: role.label }));

    if (req.method === 'GET') {
      const [userResult, invitationResult] = await Promise.all([
        clerk.users.getUserList({ limit: 100, orderBy: '-created_at' }),
        clerk.invitations.getInvitationList({ status: 'pending', limit: 100, orderBy: '-created_at' }),
      ]);
      return json({
        adminEmail: ADMIN_EMAIL,
        currentUserId: currentUser.id,
        currentUserRole: auth.role,
        roles: availableRoles,
        users: (userResult.data || []).map((user) => serializeUser(user, config)),
        invitations: (invitationResult.data || []).map((inv) => ({
          id: inv.id,
          email: String(inv.emailAddress || '').toLowerCase(),
          status: inv.status || 'pending',
          createdAt: inv.createdAt || null,
          role: normalizeRole(inv?.publicMetadata?.role || 'gebruiker', { config }),
        })),
      });
    }

    if (req.method === 'POST') {
      const body = await req.json().catch(() => ({}));
      const action = String(body?.action || 'invite');

      if (action === 'invite') {
        const email = String(body?.email || '').trim().toLowerCase();
        if (!/^\S+@\S+\.\S+$/.test(email)) return json({ error: 'Vul een geldig e-mailadres in.' }, 400);
        if (email === ADMIN_EMAIL) return json({ error: 'Dit e-mailadres is al ingesteld als hoofdbeheerder.' }, 400);
        const requestedRole = sanitizeRoleId(body?.role || 'gebruiker');
        const selected = config.roles.find((role) => role.id === requestedRole);
        if (!selected) return json({ error: 'Kies een bestaande gebruikersrol.' }, 400);

        const invitation = await clerk.invitations.createInvitation({
          emailAddress: email,
          notify: true,
          redirectUrl: new URL(req.url).origin,
          publicMetadata: { role: selected.id },
        });
        await writeAdminAudit(store, auth, 'uitgenodigd', email, [{ field: 'Rol', before: '—', after: selected.label }]);
        return json({ ok: true, invitation: { id: invitation.id, email, status: invitation.status, role: selected.id } }, 201);
      }

      if (action === 'update-user') {
        const userId = String(body?.userId || '').trim();
        if (!userId) return json({ error: 'Gebruiker ontbreekt.' }, 400);
        const firstName = String(body?.firstName || '').trim();
        const lastName = String(body?.lastName || '').trim();
        if (firstName.length > 100 || lastName.length > 100) return json({ error: 'Naam is te lang.' }, 400);
        const requestedRole = sanitizeRoleId(body?.role);
        const selected = config.roles.find((role) => role.id === requestedRole);
        if (!selected) return json({ error: 'Ongeldige gebruikersrol.' }, 400);

        const target = await clerk.users.getUser(userId);
        const beforeFirst = target.firstName || '';
        const beforeLast = target.lastName || '';
        const beforeRole = roleOf(target, config);
        const targetEmail = primaryEmailOf(target) || userId;
        const role = isOwnerUser(target) ? 'beheerder' : selected.id;
        const metadata = { ...(target.publicMetadata || {}), role };
        const updated = await clerk.users.updateUser(userId, { firstName, lastName, publicMetadata: metadata });

        const fields = [];
        if (beforeFirst !== firstName) fields.push({ field: 'Voornaam', before: beforeFirst || '—', after: firstName || '—' });
        if (beforeLast !== lastName) fields.push({ field: 'Achternaam', before: beforeLast || '—', after: lastName || '—' });
        if (beforeRole !== role) fields.push({ field: 'Rol', before: roleLabel(beforeRole, config), after: roleLabel(role, config) });
        if (fields.length) await writeAdminAudit(store, auth, 'aangepast', targetEmail, fields);
        return json({ ok: true, user: serializeUser(updated, config) });
      }

      if (action === 'revoke-invitation') {
        const invitationId = String(body?.invitationId || '').trim();
        if (!invitationId) return json({ error: 'Uitnodiging ontbreekt.' }, 400);
        const invitation = await clerk.invitations.revokeInvitation({ invitationId });
        const email = String(invitation?.emailAddress || invitationId).toLowerCase();
        await writeAdminAudit(store, auth, 'uitnodiging ingetrokken', email);
        return json({ ok: true });
      }

      return json({ error: 'Onbekende gebruikersactie.' }, 400);
    }

    if (req.method === 'DELETE') {
      const body = await req.json().catch(() => ({}));
      const userId = String(body?.userId || '').trim();
      if (!userId) return json({ error: 'Gebruiker ontbreekt.' }, 400);
      if (userId === currentUser.id) return json({ error: 'Je kunt je eigen account niet verwijderen.' }, 400);
      const target = await clerk.users.getUser(userId);
      if (isOwnerUser(target)) return json({ error: 'Het vaste hoofdbeheerderaccount kan niet worden verwijderd.' }, 400);
      const targetEmail = primaryEmailOf(target) || userId;
      const oldRole = roleOf(target, config);
      await clerk.users.deleteUser(userId);
      await writeAdminAudit(store, auth, 'verwijderd', targetEmail, [{ field: 'Rol', before: roleLabel(oldRole, config), after: '—' }]);
      return json({ ok: true });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, DELETE, OPTIONS' });
  } catch (error) {
    console.error('user-management', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
