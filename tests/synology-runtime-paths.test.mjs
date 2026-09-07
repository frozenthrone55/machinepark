import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-synology-runtime-paths.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Synology runtime path builder corrigeert alle belangrijke root-assets', () => {
  for (const name of [
    'machinepark-logo',
    'fault-library',
    'manual-library',
    'service-visits',
    'offline-first',
    'machinepark-build',
  ]) {
    assert.ok(builder.includes(name));
  }
  assert.ok(builder.includes("./index.html"));
  assert.match(builder, /start_url/);
  assert.match(builder, /scope/);
});

test('runtime path builder draait na asset-extractie', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 scripts/extract-build-assets.py'));
  assert.ok(cmd.includes('python3 build-synology-runtime-paths.py'));
  assert.ok(cmd.indexOf('python3 build-synology-runtime-paths.py') > cmd.indexOf('python3 scripts/extract-build-assets.py'));
  assert.ok(cmd.indexOf('node --check assets/machinepark-build.js') > cmd.indexOf('python3 build-synology-runtime-paths.py'));
});


test('loginruntime krijgt een inhoudshash en service worker omzeilt cache', () => {
  assert.match(builder, /hashlib\.sha256\(AUTH\.read_bytes\(\)\)/);
  assert.match(builder, /synology-local-auth\.js\?v=/);
  assert.match(builder, /updateViaCache:'none'/);
  assert.match(builder, /sw\.js\?v=/);
});


test('Synology service worker precachet volledige app-shell voor koude offline start', () => {
  assert.match(builder, /machinepark-synology-offline-shell-v1/);
  assert.match(builder, /"\.\/index\.html"/);
  assert.match(builder, /auth_asset/);
  assert.match(builder, /offline_asset/);
  assert.match(builder, /runtime_asset_pattern/);
  assert.match(builder, /fault-library/);
  assert.match(builder, /manual-library/);
  assert.match(builder, /service-visits/);
  assert.match(builder, /assets\/machinepark-build/);
  assert.match(builder, /fixed_assets = sorted\(critical_assets\)/);
});


test('offline runtime krijgt een inhoudshash', () => {
  assert.match(builder, /OFFLINE = ROOT \/ "offline-first\.js"/);
  assert.match(builder, /hashlib\.sha256\(OFFLINE\.read_bytes\(\)\)/);
  assert.match(builder, /offline-first\.js\?v=/);
});

test('Synology service worker laat PHP API en no-store altijd rechtstreeks naar netwerk', () => {
  assert.match(builder, /machinepark-synology-api-network-only-v1/);
  assert.match(builder, /url\.pathname\.includes\('\/synology\/api\/'\)/);
  assert.match(builder, /e\.request\.cache==='no-store'/);
  assert.match(builder, /e\.respondWith\(fetch\(e\.request\)\)/);
});

test('Synology dashboard toont automatisch datum en uur van laatste gepubliceerde build', () => {
  assert.match(builder, /dashboardVersionStamp/);
  assert.match(builder, /accountSummary/);
  assert.match(builder, /Laatste versie: laden/);
  assert.match(builder, /data-machinepark-synology-version="v3"/);
  assert.match(builder, /\.\/deploy-meta\.json\?ts=/);
  assert.match(builder, /cache: 'no-store'/);
  assert.match(builder, /timeZone: 'Europe\/Brussels'/);
  assert.match(builder, /new Intl\.DateTimeFormat\('nl-BE'/);
  assert.match(builder, /Laatste versie: ' \+ formatted/);
  assert.match(builder, /visibilitychange/);
});

test('versiedatum staat direct boven de aangemelde gebruiker', () => {
  const versionPos = builder.indexOf('id="dashboardVersionStamp"');
  const accountPos = builder.indexOf('id="accountSummary"');
  assert.ok(versionPos >= 0 && accountPos >= 0);
  assert.match(builder, /account_anchor/);
  assert.match(builder, /account_stamp/);
  assert.match(builder, /grid-template-areas:'version version' 'copy user'/);
  assert.match(builder, /justify-self:end/);
  assert.match(builder, /data-machinepark-synology-version="v3"/);
  assert.doesNotMatch(builder, /sync_anchor/);
});

test('offline opstart kan ook doorgaan wanneer browser onterecht online rapporteert', () => {
  const offline = readFileSync(new URL('../offline-first.js', import.meta.url), 'utf8');
  assert.match(offline, /machineparkOfflineBootRequested === true/);
  assert.match(offline, /machineparkTryOfflineSession\(\{ force: true \}\)/);
  assert.match(offline, /let offlineBootPromise = null/);
  assert.match(offline, /window\.machineparkOfflineBootRequested = false/);
});
