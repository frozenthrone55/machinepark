import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const auth = readFileSync(new URL('../synology/api/auth.php', import.meta.url), 'utf8');
const lib = readFileSync(new URL('../synology/api/_auth-lib.php', import.meta.url), 'utf8');
const runtime = readFileSync(new URL('../synology-local-auth.js', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-auth.py', import.meta.url), 'utf8');

test('lokale gebruikers worden buiten de webroot opgeslagen', () => {
  assert.match(lib, /\/volume1\/MachineparkData\/data\/users\.json/);
  assert.match(lib, /LOCK_EX/);
  assert.match(lib, /rename\(\$tmp, MP_USERS_FILE\)/);
});

test('auth is compatibel met PHP 7.2 en gebruikt sessies', () => {
  assert.match(lib, /session_name\('MACHINEPARKSESSID'\)/);
  assert.match(lib, /session_set_cookie_params\(0,/);
  assert.match(lib, /httponly|true\);/i);
  assert.doesNotMatch(lib, /session_set_cookie_params\(\[/);
});

test('wachtwoorden worden gehasht en geverifieerd', () => {
  assert.match(auth, /password_hash\(/);
  assert.match(auth, /PASSWORD_DEFAULT/);
  assert.match(auth, /password_verify\(/);
  assert.match(auth, /minstens 10 tekens/);
});

test('eerste lokale beheerder kan slechts eenmaal worden ingesteld', () => {
  assert.match(auth, /De lokale gebruikers zijn al ingesteld/);
  assert.match(auth, /'isOwner' => true/);
  assert.match(auth, /session_regenerate_id\(true\)/);
});

test('lokale browserruntime heeft setup login logout en geen externe auth nodig', () => {
  assert.match(runtime, /synology\/api\/auth\.php/);
  assert.match(runtime, /Lokale beheerder aanmaken/);
  assert.match(runtime, /action: 'login'/);
  assert.match(runtime, /action: 'logout'/);
  assert.match(runtime, /synology-local-session/);
});

test('build verwijdert Clerk boot en gebruikt relatieve paden', () => {
  assert.match(builder, /synology-local-auth-v1/);
  assert.match(builder, /synology-local-auth\.js/);
  assert.match(builder, /machinepark-logo\.svg/);
  assert.match(builder, /netlify\/functions\/clerk-config/);
});
