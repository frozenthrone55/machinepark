import { createClerkClient, verifyToken } from '@clerk/backend';
import {
  ROLE_CONFIG_KEY,
  defaultRoleConfig,
  normalizeRole,
  normalizeRoleConfig,
  permissionsForRole,
} from './permissions.mjs';

export const ADMIN_EMAIL = 'kriskoffieapp@telenet.be';
export const STORE_NAME = 'machinepark-central';
export const NO_STORE = { 'cache-control': 'no-store, max-age=0' };

export function jsonResponse(data, status = 200, headers = {}) {
  return Response.json(data, { status, headers: { ...NO_STORE, ...headers } });
}

export function emailsOf(user) {
  return (user?.emailAddresses || [])
    .map((item) => String(item?.emailAddress || '').trim().toLowerCase())
    .filter(Boolean);
}

export function primaryEmailOf(user) {
  const primary = (user?.emailAddresses || []).find((item) => item.id === user?.primaryEmailAddressId);
  return String(primary?.emailAddress || user?.emailAddresses?.[0]?.emailAddress || '').trim().toLowerCase();
}

export async function authenticateClerk(req) {
  const secretKey = process.env.CLERK_SECRET_KEY;
  if (!secretKey) {
    throw Object.assign(new Error('CLERK_SECRET_KEY is niet ingesteld in Netlify.'), { status: 500 });
  }

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
  const user = await clerk.users.getUser(verified.sub);
  const email = primaryEmailOf(user);
  const name = [user?.firstName, user?.lastName].filter(Boolean).join(' ').trim();
  const owner = emailsOf(user).includes(ADMIN_EMAIL);

  return {
    ...verified,
    sub: verified.sub,
    verified,
    clerk,
    user,
    email,
    name,
    owner,
    rawRole: user?.publicMetadata?.role || 'gebruiker',
  };
}

export async function loadRoleConfig(store) {
  const entry = await store.getWithMetadata(ROLE_CONFIG_KEY, { type: 'json', consistency: 'strong' });
  return {
    entry,
    config: normalizeRoleConfig(entry?.data || defaultRoleConfig()),
  };
}

export async function resolveRoleAccess(store, auth) {
  const { entry, config } = await loadRoleConfig(store);
  const role = normalizeRole(auth?.rawRole, { owner: Boolean(auth?.owner), config });
  return {
    ...auth,
    role,
    roleConfig: config,
    roleConfigEtag: entry?.etag || null,
    permissions: permissionsForRole(role, config, { owner: Boolean(auth?.owner) }),
  };
}
