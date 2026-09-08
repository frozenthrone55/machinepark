import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-actions.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const nav = readFileSync(new URL('../build-navigation-runtime.py', import.meta.url), 'utf8');
const service = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const dataApi = readFileSync(new URL('../synology/api/machinepark-data.php', import.meta.url), 'utf8');
const userApi = readFileSync(new URL('../synology/api/action-users.php', import.meta.url), 'utf8');
const auditLib = readFileSync(new URL('../synology/api/_audit-lib.php', import.meta.url), 'utf8');
const auditLog = readFileSync(new URL('../synology/api/audit-log.php', import.meta.url), 'utf8');
const roleLib = readFileSync(new URL('../synology/api/_role-lib.php', import.meta.url), 'utf8');

test('Acties is een eigen offline datastore met DB-migratie', () => {
  assert.match(builder, /DB_VERSION=2/);
  assert.match(builder, /breakdowns','actions/);
  assert.match(builder, /actions:\\[\\]/);
  assert.match(builder, /put\\('actions'/);
});

test('Acties heeft twee lijsten, snel toevoegen en afronden', () => {
  assert.match(builder, /Nog te doen/);
  assert.match(builder, /Uitgevoerd/);
  assert.match(builder, /actionQuickInput/);
  assert.match(builder, /quickAddAction/);
  assert.match(builder, /openCompleteAction/);
  assert.match(builder, /completedByName/);
  assert.match(builder, /30\\*86400000/);
  assert.match(builder, /reopenAction/);
});

test('Acties ondersteunt gebruiker toestel context en historiek', () => {
  assert.match(builder, /action-users\\.php/);
  assert.match(builder, /assigneeName/);
  assert.match(builder, /actionDeviceSearchField/);
  assert.match(builder, /historyEntry/);
  assert.match(builder, /decorateDeviceModal/);
  assert.match(builder, /decorateContextModal\\('maintenance'/);
  assert.match(builder, /decorateContextModal\\('breakdown'/);
  assert.match(service, /machineparkDecorateServiceReportActions/);
});

test('Acties verschijnt op dashboard en navigatie', () => {
  assert.match(builder, /kpiActions/);
  assert.match(builder, /actionNavCount/);
  assert.match(nav, /actions: \\['Acties'/);
  assert.match(nav, /machineparkRenderActions/);
});

test('Acties bouwt als laatste feature voor assetextractie', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-actions.py'));
  assert.ok(cmd.indexOf('python3 build-actions.py') > cmd.indexOf('python3 build-synology-cloud-import.py'));
  assert.ok(cmd.indexOf('python3 build-actions.py') < cmd.indexOf('python3 scripts/check-inline-scripts.py'));
});

test('Synology beschermt acties tegen oude clients en audit kan acties herstellen', () => {
  assert.match(dataApi, /Oudere clients kennen de Acties-store/);
  assert.match(dataApi, /\\$data\\['actions'\\]/);
  assert.match(auditLib, /'actions' => 'Acties'/);
  assert.match(auditLib, /breakdowns','actions/);
  assert.match(auditLog, /breakdowns','actions/);
});

test('Actiegebruikers-API deelt alleen minimale gebruikersinfo met aangemelde gebruikers', () => {
  assert.match(userApi, /mp_auth_require_user/);
  assert.match(userApi, /mp_auth_public_user/);
  assert.match(userApi, /roleLabel/);
  assert.doesNotMatch(userApi, /passwordHash/);
});

test('Acties heeft een expliciet Synology-weergaverecht en blijft zichtbaar voor bestaande ingebouwde rollen', () => {
  assert.match(roleLib, /view\.actions/);
  assert.match(roleLib, /Acties bekijken/);
  assert.match(roleLib, /view\.manuals','view\.actions','view\.parts/);
  assert.match(roleLib, /view\.dashboard','view\.actions','view\.parts/);
  assert.match(builder, /breakdowns','actions','faults/);
});
