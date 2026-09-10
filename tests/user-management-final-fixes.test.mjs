import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const builder = fs.readFileSync('build-user-management-final-fixes.py', 'utf8');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));

test('finale gebruikerslaag maakt geïmporteerde accounts duidelijk herkenbaar', () => {
  assert.match(builder, /Lokaal wachtwoord instellen/);
  assert.match(builder, /Wachtwoord instellen/);
  assert.match(builder, /user\.needsPassword/);
  assert.match(builder, /user-status-setup/);
});

test('verwijderde cloudgebruiker kan niet opnieuw materialiseren', () => {
  assert.match(builder, /function user_forget_cloud_reference/);
  assert.match(builder, /user_forget_cloud_reference\(\(string\)\(\$target\['email'\]/);
  assert.match(builder, /cloudgebruiker kon niet definitief uit de referentielijst/);
});

test('gebruikersbeheer toont alleen rollen die actor mag toewijzen', () => {
  assert.match(builder, /function user_available_roles_for_actor/);
  assert.match(builder, /user_permissions_subset/);
  assert.match(builder, /user_available_roles_for_actor\(\$currentUser\)/);
});

test('finale gebruikerslaag draait direct na hardening', () => {
  const build = pkg.scripts.build;
  const hardening = build.indexOf('build-user-management-hardening.py');
  const finalFix = build.indexOf('build-user-management-final-fixes.py');
  const content = build.indexOf('build-synology-local-content.py');
  assert.ok(hardening >= 0 && finalFix > hardening && content > finalFix);
});
