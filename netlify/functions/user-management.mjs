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

function primaryEmailOf(user) {
  const primary = (user?.emailAddresses || []).find((x) => x.id === user?.primaryEmailAddressId);
  return String(primary?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
}

function isAdminUser(user) {
  return emailsOf(user).includes(ADMIN_EMAIL);
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
  if (!isAdminUser(currentUser)) {
    throw Object.assign(new Error('Alleen de beheerder heeft toegang tot gebruikersbeheer.'), { status: 403 });
  }

  return { clerk, currentUser, verified };
}

async function writeAdminAudit(currentUser, verified, action, label, fields = []) {
  try {
    const store = getStore({ name: STORE_NAME, consistency: 'strong' });
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(currentUser) || verified.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: verified.sub,
      userEmail: email,
      userName: [currentUser.firstName, currentUser.lastName].filter(Boolean).join(' '),
      changeCount: 1,
      changes: [{ entityType: 'Gebruikersbeheer', entityId: label, entityLabel: label, action, fields }],
      truncated: false,
    }, { metadata: { at, userId: verified.sub, userEmail: email } });
  } catch (error) {
    console.error('gebruikersbeheer audit', error);
  }
}

function serializeUser(user) {
  const email = primaryEmailOf(user);
  return {
    id: user.id,
    email,
    firstName: user.firstName || '',
    lastName: user.lastName || '',
    fullName: [user.firstName, user.lastName].filter(Boolean).join(' '),
    role: email === ADMIN_EMAIL ? 'beheerder' : 'gebruiker',
    imageUrl: user.imageUrl || '',
    lastSignInAt: user.lastSignInAt || null,
    createdAt: user.createdAt || null,
    banned: Boolean(user.banned),
    locked: Boolean(user.locked),
  };
}

export default async (req) => {
  if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: NO_STORE });

  try {
    const { clerk, currentUser, verified } = await authenticateAdmin(req);

    if (req.method === 'GET') {
      const [userResult, invitationResult] = await Promise.all([
        clerk.users.getUserList({ limit: 100, orderBy: '-created_at' }),
        clerk.invitations.getInvitationList({ status: 'pending', limit: 100, orderBy: '-created_at' }),
      ]);

      return json({
        adminEmail: ADMIN_EMAIL,
        currentUserId: currentUser.id,
        users: (userResult.data || []).map(serializeUser),
        invitations: (invitationResult.data || []).map((inv) => ({
          id: inv.id,
          email: String(inv.emailAddress || '').toLowerCase(),
          status: inv.status || 'pending',
          createdAt: inv.createdAt || null,
        })),
      });
    }

    if (req.method === 'POST') {
      const body = await req.json().catch(() => ({}));
      const action = String(body?.action || 'invite');

      if (action === 'invite') {
        const email = String(body?.email || '').trim().toLowerCase();
        if (!/^\S+@\S+\.\S+$/.test(email)) return json({ error: 'Vul een geldig e-mailadres in.' }, 400);
        if (email === ADMIN_EMAIL) return json({ error: 'Dit e-mailadres is al ingesteld als beheerder.' }, 400);

        const invitation = await clerk.invitations.createInvitation({
          emailAddress: email,
          notify: true,
          redirectUrl: new URL(req.url).origin,
          publicMetadata: { role: 'gebruiker' },
        });
        await writeAdminAudit(currentUser, verified, 'uitgenodigd', email, [{ field: 'Rol', before: '—', after: 'Gebruiker' }]);
        return json({ ok: true, invitation: { id: invitation.id, email, status: invitation.status } }, 201);
      }

      if (action === 'revoke-invitation') {
        const invitationId = String(body?.invitationId || '').trim();
        if (!invitationId) return json({ error: 'Uitnodiging ontbreekt.' }, 400);
        const invitation = await clerk.invitations.revokeInvitation({ invitationId });
        const email = String(invitation?.emailAddress || invitationId).toLowerCase();
        await writeAdminAudit(currentUser, verified, 'uitnodiging ingetrokken', email);
        return json({ ok: true });
      }

      return json({ error: 'Onbekende gebruikersactie.' }, 400);
    }

    if (req.method === 'DELETE') {
      const body = await req.json().catch(() => ({}));
      const userId = String(body?.userId || '').trim();
      if (!userId) return json({ error: 'Gebruiker ontbreekt.' }, 400);
      if (userId === currentUser.id) return json({ error: 'Je kunt je eigen beheerderaccount niet verwijderen.' }, 400);

      const target = await clerk.users.getUser(userId);
      if (isAdminUser(target)) return json({ error: 'Het beheerderaccount kan niet worden verwijderd.' }, 400);
      const targetEmail = primaryEmailOf(target) || userId;

      await clerk.users.deleteUser(userId);
      await writeAdminAudit(currentUser, verified, 'verwijderd', targetEmail);
      return json({ ok: true });
    }

    return json({ error: 'Methode niet toegestaan.' }, 405, { allow: 'GET, POST, DELETE, OPTIONS' });
  } catch (error) {
    console.error('user-management', error);
    return json({ error: error?.message || 'Onbekende serverfout.' }, error?.status || 500);
  }
};
