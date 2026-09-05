import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../synology/migrate-media.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-media-migration.py', import.meta.url), 'utf8');

test('media migratie scant alleen oude Netlify fotoreferenties', () => {
  assert.match(page, /\/\.netlify\/functions\/device-photos/);
  assert.match(page, /\/\.netlify\/functions\/part-photos/);
  assert.match(page, /\/\.netlify\/functions\/service-photos/);
  assert.match(page, /media_scan/);
});

test('media migratie maakt eerst veiligheidsback-up en werkt per foto', () => {
  assert.match(page, /media-migration-before-/);
  assert.match(page, /migrate-one/);
  assert.match(page, /media_replace_ref/);
  assert.match(page, /media_state_write/);
  assert.match(page, /LOCK_EX/);
});

test('media migratie schrijft naar lokale Synology fotomappen', () => {
  assert.match(page, /\/devices\//);
  assert.match(page, /\/parts\//);
  assert.match(page, /\/service\//);
  assert.match(page, /device-photos\.php/);
  assert.match(page, /part-photos\.php/);
  assert.match(page, /service-photos\.php/);
});

test('bronadres is beperkt tot openbaar HTTPS en redirects worden niet gevolgd', () => {
  assert.match(page, /scheme.*https/s);
  assert.match(page, /FILTER_FLAG_NO_PRIV_RANGE/);
  assert.match(page, /CURLOPT_FOLLOWLOCATION, false/);
  assert.match(page, /follow_location.*0/s);
});

test('Beheer krijgt een lokale migratiekoppeling', () => {
  assert.match(builder, /synology\/migrate-media\.php/);
  assert.match(builder, /Oude cloudfoto/);
});
