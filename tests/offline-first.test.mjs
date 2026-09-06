import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const offline = fs.readFileSync('offline-first.js', 'utf8');
const sw = fs.readFileSync('sw.js', 'utf8');
const index = fs.readFileSync('index.html', 'utf8');
const packageJson = JSON.parse(fs.readFileSync('package.json', 'utf8'));

test('offline-first runtime bevat geldige JavaScript', () => {
  assert.doesNotThrow(() => new vm.Script(offline, { filename: 'offline-first.js' }));
});

test('offline-first runtime bewaart lokale wijzigingen en merge-informatie', () => {
  assert.match(offline, /MachineparkOfflineSyncDB/);
  assert.match(offline, /machinepark-offline-access-v1/);
  assert.match(offline, /mergeOfflineSnapshots/);
  assert.match(offline, /markDirty/);
  assert.match(offline, /machineparkFlushOfflinePhotos/);
});

test('offline-first runtime synchroniseert automatisch bij reconnect', () => {
  assert.match(offline, /addEventListener\('offline'/);
  assert.match(offline, /addEventListener\('online'/);
  assert.match(offline, /Verbinding hersteld/);
  assert.match(offline, /centralPush = async function/);
});

test('gelijktijdige offline en online voorraadwijzigingen worden als delta samengevoegd', () => {
  assert.match(offline, /storeName === 'parts' && key === 'stock'/);
  assert.match(offline, /baseStock \+ \(localStock - baseStock\) \+ \(remoteStock - baseStock\)/);
  assert.match(offline, /mergeEntity\(base\.get\(id\), local\.get\(id\), remote\.get\(id\), stats, storeName\)/);
});

test('gebouwde app laadt de offline runtime met actuele versie om oude PWA-cache te breken', () => {
  assert.equal(packageJson.version, '1.68.9');
  assert.match(index, /\/offline-first\.js\?v=1\.68\.9/);
  assert.match(index, /data-machinepark-offline-first="1"/);
  assert.match(sw, /'\/offline-first\.js\?v=1\.68\.9'/);
});

test('service worker cachet offline runtime en cachebare API-data', () => {
  assert.match(sw, /offline-first\.js/);
  assert.match(sw, /work-order-templates/);
  assert.match(sw, /device-photos/);
  assert.match(sw, /service-photos/);
});


test('mislukte push start geen snelle retrylus', () => {
  assert.match(offline, /let pushFailed = false/);
  assert.match(offline, /pushFailed = true/);
  assert.match(offline, /if \(!pushFailed && centralSync\.pending && centralSync\.enabled && navigator\.onLine\)/);
  assert.match(offline, /Synchronisatie wacht op controle/);
});


test('dirty opstart blokkeert Machinepark niet als centrale push faalt', () => {
  assert.match(offline, /Lokale wijzigingen mogen de appstart nooit blokkeren/);
  assert.match(offline, /Opstartsynchronisatie mislukt; lokale gegevens blijven actief/);
  assert.match(offline, /Synchronisatie wacht op controle/);
});


test('sync-stabiliteitsbuilder draait na drift-herstel', () => {
  const cmd = packageJson.scripts.build;
  assert.ok(cmd.includes('python3 build-sync-status-stability.py'));
  assert.ok(cmd.indexOf('python3 build-sync-status-stability.py') > cmd.indexOf('python3 build-sync-drift-recovery.py'));
});


test('grote Synology snapshots worden gecomprimeerd en syncfouten tonen HTTP-status', () => {
  assert.match(offline, /CompressionStream\('gzip'\)/);
  assert.match(offline, /Content-Encoding.*gzip/);
  assert.match(offline, /payloadBytes >= 128 \* 1024/);
  assert.match(offline, /HTTP ' \+ status/);
  assert.match(offline, /syncErrorStatus/);
});
