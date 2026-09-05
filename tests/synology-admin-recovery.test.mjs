import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../synology/admin-recovery.php', import.meta.url), 'utf8');

test('adminherstel werkt alleen via intern NAS-adres', () => {
  assert.match(page, /mp_auth_is_local_ip\(\$client\)/);
  assert.match(page, /mp_auth_is_private_host\(\$host\)/);
  assert.match(page, /mp_auth_is_public_host\(\$host\)/);
  assert.match(page, /uitsluitend via het interne NAS-adres/);
});

test('adminherstel vereist een eenmalige herstelcode van de NAS', () => {
  assert.match(page, /\/volume1\/MachineparkData\/admin-recovery-code\.txt/);
  assert.match(page, /hash_equals\(\$expected, \$submittedCode\)/);
  assert.match(page, /random_int/);
  assert.match(page, /@unlink\(MP_RECOVERY_CODE_FILE\)/);
});

test('adminherstel wijzigt alleen het bestaande beheeraccount', () => {
  assert.match(page, /recovery_select_admin/);
  assert.match(page, /count\(\$candidates\) === 1/);
  assert.match(page, /\['username'\] = 'admin'/);
  assert.match(page, /\['isOwner'\] = true/);
  assert.match(page, /\['role'\] = 'beheerder'/);
  assert.match(page, /password_hash\(\$newPassword/);
});

test('adminherstel wist geen Machinepark-data', () => {
  assert.doesNotMatch(page, /state-v1\.json/);
  assert.doesNotMatch(page, /fault-library-v1\.json/);
  assert.doesNotMatch(page, /manual-library-v1\.json/);
  assert.doesNotMatch(page, /rm -rf|unlink\([^)]*MachineparkData/);
});
