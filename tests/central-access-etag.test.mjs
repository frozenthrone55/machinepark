import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const offline = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
const server = readFileSync(new URL('../netlify/functions/machinepark-data.mjs', import.meta.url), 'utf8');
const permissions = readFileSync(new URL('../netlify/functions/_shared/permissions.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('centrale pull gebruikt eigen ETag-header zodat JSON met rechten behouden blijft', () => {
  assert.match(offline, /machinepark-central-access-etag-v1/);
  assert.match(offline, /headers\['X-Machinepark-If-None-Match'\] = etag/);

  const anchor = offline.indexOf('machinepark-central-access-etag-v1');
  const section = offline.slice(anchor, anchor + 1000);
  assert.doesNotMatch(section, /headers\['If-None-Match'\] = etag/);
});

test('server gebruikt eigen ETag-header en stuurt bij unchanged actuele toegang mee', () => {
  assert.match(server, /req\.headers\.get\('x-machinepark-if-none-match'\)/);
  assert.match(server, /unchanged: true/);
  assert.match(server, /\.\.\.accessPayload\(auth\)/);
  assert.match(server, /permissions: auth\.permissions/);
});

test('nieuwe storingenrechten bestaan in de actuele serverrechten', () => {
  assert.match(permissions, /view\.faults/);
  assert.match(permissions, /faults\.manage/);
});

test('toegangsrefresh blijft aanwezig in versie 1.68.3', () => {
  assert.equal(packageJson.version, '1.68.3');
  assert.match(packageJson.scripts.build, /build-central-access-etag\.py/);
});
