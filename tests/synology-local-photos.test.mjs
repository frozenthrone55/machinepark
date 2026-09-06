import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const lib = readFileSync(new URL('../synology/api/_photo-lib.php', import.meta.url), 'utf8');
const device = readFileSync(new URL('../synology/api/device-photos.php', import.meta.url), 'utf8');
const part = readFileSync(new URL('../synology/api/part-photos.php', import.meta.url), 'utf8');
const service = readFileSync(new URL('../synology/api/service-photos.php', import.meta.url), 'utf8');
const purge = readFileSync(new URL('../synology/api/purge-service-audit-photos.php', import.meta.url), 'utf8');
const builder = readFileSync(new URL('../build-synology-local-photos.py', import.meta.url), 'utf8');

test('foto’s worden buiten webroot opgeslagen', () => {
  assert.match(lib, /\/volume1\/MachineparkData\/photos/);
  assert.match(device, /\/devices\//);
  assert.match(part, /\/parts\//);
  assert.match(service, /\/service\//);
});

test('lokale foto-opslag valideert afbeeldingen en bewaart thumbnails', () => {
  assert.match(lib, /data:\(image\//);
  assert.match(lib, /180000|thumb/);
  assert.match(lib, /\.thumb\.bin/);
  assert.match(lib, /image\/jpeg/);
});

test('foto-API’s vereisen lokale sessie en rolrechten', () => {
  for (const source of [device, part, service]) {
    assert.match(source, /mp_photo_require_local_user/);
    assert.match(source, /mp_photo_can/);
  }
});

test('servicefoto’s worden bij verwijderen ook lokaal opgeschoond', () => {
  assert.match(purge, /mp_photo_remove_directory/);
  assert.match(purge, /MP_AUDIT_DIR/);
  assert.match(purge, /maintenance\.delete|maintenance/);
  assert.match(purge, /breakdowns\.delete|breakdowns/);
});

test('Synology build vervangt alle foto-endpoints en Clerk purge-token', () => {
  assert.match(builder, /device-photos\.php/);
  assert.match(builder, /part-photos\.php/);
  assert.match(builder, /service-photos\.php/);
  assert.match(builder, /purge-service-audit-photos\.php/);
  assert.match(builder, /centralHeaders\(true\)/);
  assert.match(builder, /CACHEABLE_API=new Set\(\[\]\)/);
});

test('servicefoto API herstelt stale refs en dedupliceert identieke beelden', () => {
  assert.match(service, /machinepark-service-photo-self-heal-v1/);
  assert.match(service, /if\(!mp_photo_exists\(\$base\)\)continue/);
  assert.match(service, /hash_file\('sha256',\$base\.'\.bin'\)/);
  assert.match(service, /hash\('sha256',\$parsed\['bytes'\]\)/);
  assert.match(service, /\$seenHashes=\[\]/);
  assert.match(service, /if\(isset\(\$seenHashes\[\$hash\]\)\)continue/);
});
test('Synology foto-API gebruikt canonieke machinepark-route en compacte HTTP-fouten', () => {
  assert.match(lib, /return '\/machinepark\/synology\/api\/'/);
  assert.match(builder, /index = index\.replace\("\.\/synology\/api\/", "\/machinepark\/synology\/api\/"\)/);
  assert.match(builder, /credentials: 'same-origin'/);
  assert.match(builder, /machineparkLastPhotoError/);
  assert.match(builder, /HTTP /);
  assert.match(builder, /<script/);
});
