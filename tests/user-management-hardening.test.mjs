import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const php = fs.readFileSync('synology/api/user-management.php', 'utf8');
const builder = fs.readFileSync('build-user-management-hardening.py', 'utf8');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));

test('Synology user API exposes and manages blocked state safely', () => {
  assert.match(php, /\$public\['disabled'\] = !empty\(\$user\['disabled'\]\)/);
  assert.match(php, /if \(\$action === 'toggle-user'\)/);
  assert.match(php, /vaste hoofdbeheerder kan niet worden geblokkeerd/i);
  assert.match(php, /eigen actieve account niet blokkeren/i);
});

test('Synology user API validates unique email and username', () => {
  assert.match(php, /function user_assert_unique/);
  assert.match(php, /Er bestaat al een gebruiker met dit e-mailadres/);
  assert.match(php, /Er bestaat al een gebruiker met deze gebruikersnaam/);
  assert.match(php, /function user_validate_username/);
});

test('Synology user editor supports identity, role and password changes', () => {
  assert.match(php, /\$target\['email'\] = \$newEmail/);
  assert.match(php, /\$target\['username'\] = \$newUsername/);
  assert.match(php, /password_hash\(\$newPassword, PASSWORD_DEFAULT\)/);
  assert.match(php, /mp_role_exists\(\$role\)/);
});

test('generated user management has all account actions', () => {
  for (const needle of [
    'inviteUserFirstName',
    'inviteUserLastName',
    'inviteUserUsername',
    "action: 'create-user'",
    "action: 'toggle-user'",
    'data-remove-user',
    'Nieuw wachtwoord',
    'Hoofdbeheerder',
  ]) assert.ok(builder.includes(needle), `missing ${needle}`);
});

test('hardening builder runs after Synology local admin conversion', () => {
  const build = pkg.scripts.build;
  const admin = build.indexOf('build-synology-local-admin.py');
  const hardening = build.indexOf('build-user-management-hardening.py');
  assert.ok(admin >= 0 && hardening > admin);
});
