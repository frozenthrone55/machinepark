import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const lib = readFileSync(new URL('../synology/api/_auth-lib.php', import.meta.url), 'utf8');
const auth = readFileSync(new URL('../synology/api/auth.php', import.meta.url), 'utf8');
const photos = readFileSync(new URL('../synology/api/_photo-lib.php', import.meta.url), 'utf8');

test('publiek Synology-adres is expliciet HTTPS-only en geallowlist', () => {
  assert.match(lib, /krisooms\.synology\.me/);
  assert.match(lib, /mp_auth_public_hosts/);
  assert.match(lib, /mp_auth_request_is_https/);
  assert.match(lib, /external-http-blocked/);
});

test('lokale IP-toegang blijft toegestaan zonder HTTPS', () => {
  assert.match(lib, /mp_auth_is_private_host/);
  assert.match(lib, /mp_auth_is_local_ip\(\$clientIp\)/);
});

test('mutaties op het publieke adres vereisen same-origin HTTPS', () => {
  assert.match(lib, /mp_auth_mutation_origin_valid/);
  assert.match(lib, /HTTP_ORIGIN/);
  assert.match(lib, /INVALID_ORIGIN/);
});

test('sessiecookies worden Secure achter HTTPS en blijven HttpOnly', () => {
  assert.match(lib, /session\.use_strict_mode/);
  assert.match(lib, /session\.use_only_cookies/);
  assert.match(lib, /mp_auth_request_is_https\(\)/);
  assert.match(lib, /session_set_cookie_params\(0, '\/machinepark\/', '', \$secure, true\)/);
});

test('login heeft brute-force rate limiting', () => {
  assert.match(auth, /MP_LOGIN_RATE_FILE/);
  assert.match(auth, /auth_rate_status/);
  assert.match(auth, /auth_rate_fail/);
  assert.match(auth, /auth_rate_success/);
  assert.match(auth, /login_rate_limited/);
  assert.match(auth, /Retry-After/);
});

test('foto-endpoints gebruiken dezelfde centrale request policy', () => {
  assert.match(photos, /mp_auth_require_request_access/);
  assert.match(photos, /mp_auth_access_error_payload/);
});
