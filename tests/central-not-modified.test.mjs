import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const offline = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('HTTP 304 wordt als geldige ongewijzigde synchronisatie behandeld', () => {
  assert.match(offline, /machinepark-central-304-not-modified-v1/);
  assert.match(offline, /if \(res\.status === 304\)/);
  assert.match(offline, /unchanged: true/);
  assert.match(offline, /Centraal gesynchroniseerd · geen wijzigingen/);

  const anchor = offline.indexOf("const etag = meta.etag || centralSync.etag || null;");
  const end = offline.indexOf('if (!body.exists)', anchor);
  assert.ok(anchor >= 0 && end > anchor, 'centrale ETag-ophaalsectie ontbreekt');
  const section = offline.slice(anchor, end);
  assert.ok(section.indexOf('if (res.status === 304)') >= 0, '304-afhandeling ontbreekt');
  assert.ok(section.indexOf('if (!res.ok)') >= 0, 'algemene HTTP-foutafhandeling ontbreekt');
  assert.ok(section.indexOf('if (res.status === 304)') < section.indexOf('if (!res.ok)'), '304 moet vóór de algemene foutcontrole worden verwerkt');
});

test('304 behoudt lokale data en bestaande ETag', () => {
  assert.match(offline, /centralSync\.etag = etag \|\| centralSync\.etag \|\| null/);
  assert.match(offline, /writeMeta\(\{ etag: centralSync\.etag \|\| null, dirty: false \}\)/);
  assert.match(offline, /data: null/);
});

test('304-fix blijft als vangnet aanwezig in versie 1.68.6', () => {
  assert.equal(packageJson.version, '1.68.6');
  assert.match(packageJson.scripts.build, /build-central-not-modified\.py/);
  assert.match(packageJson.scripts.build, /build-central-access-etag\.py/);
});
