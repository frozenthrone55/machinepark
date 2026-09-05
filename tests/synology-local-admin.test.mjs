import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const users = readFileSync(new URL('../synology/api/user-management.php', import.meta.url), 'utf8');
const roles = readFileSync(new URL('../synology/api/role-management.php', import.meta.url), 'utf8');
const audit = readFileSync(new URL('../synology/api/audit-log.php', import.meta.url), 'utf8');
const roleLib = readFileSync(new URL('../synology/api/_role-lib.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-admin.py', import.meta.url), 'utf8');

test('lokale gebruikers worden rechtstreeks met gehasht wachtwoord aangemaakt', () => {
  assert.match(users, /create-user/);
  assert.match(users, /password_hash\(/);
  assert.match(users, /minstens 10 tekens/);
  assert.match(users, /De vaste hoofdbeheerder kan niet worden verwijderd/);
});

test('rollen en rechten worden lokaal buiten webroot opgeslagen', () => {
  assert.match(roleLib, /\/volume1\/MachineparkData\/data\/role-config-v1\.json/);
  assert.match(roleLib, /PERMISSION|permission/i);
  assert.match(roles, /save-role/);
  assert.match(roles, /delete-role/);
  assert.match(roles, /role_usage_count/);
});

test('lokaal logboek ondersteunt lezen en veilig ongedaan maken', () => {
  assert.match(audit, /mp_audit_list/);
  assert.match(audit, /audit\.undo/);
  assert.match(audit, /restore-fields/);
  assert.match(audit, /remove-added/);
  assert.match(audit, /restore-deleted/);
});

test('Synology build verwijdert Netlify beheerendpoints', () => {
  assert.match(builder, /synology\/api\/user-management\.php/);
  assert.match(builder, /synology\/api\/role-management\.php/);
  assert.match(builder, /synology\/api\/audit-log\.php/);
  assert.match(builder, /inviteUserPassword/);
  assert.match(builder, /create-user/);
});
