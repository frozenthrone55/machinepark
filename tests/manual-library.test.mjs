import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-manual-library.py', import.meta.url), 'utf8');
const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const endpoint = readFileSync(new URL('../netlify/functions/manual-library.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Handleidingen krijgt een eigen pagina en beheerkaart', () => {
  assert.match(build, /data-view=\\?"manuals\\?"/);
  assert.match(build, /id=\\?"view-manuals\\?"/);
  assert.match(build, /manualLibrarySettingsCard/);
  assert.match(build, /\+ Handleiding toevoegen/);
  assert.match(build, /Alle merken/);
  assert.match(build, /Alle modellen/);
  assert.match(build, /Alle types/);
});

test('handleidingen kunnen algemeen merk model of toestelgebonden zijn', () => {
  assert.match(client, /manual\.deviceId/);
  assert.match(client, /manual\?\.brand && manual\?\.model/);
  assert.match(client, /Algemeen · alle toestellen/);
  assert.match(client, /manualAppliesToDevice/);
  assert.match(client, /deviceId: String\(formData\.get\('deviceId'\)/);
});

test('PDF-bestanden staan apart centraal en worden gevalideerd', () => {
  assert.match(endpoint, /FILE_PREFIX = 'manual-files\/'/);
  assert.match(endpoint, /MAX_FILE_BYTES = 12_000_000/);
  assert.match(endpoint, /application\/pdf/);
  assert.match(endpoint, /%PDF-/);
  assert.match(endpoint, /action === 'save-manual'/);
  assert.match(endpoint, /action === 'delete-manual'/);
  assert.match(endpoint, /authenticateClerk/);
});

test('technieker kan passende handleidingen vanuit toestel en depannage openen', () => {
  assert.match(client, /Handleidingen voor dit toestel/);
  assert.match(client, /Handleidingen voor deze depannage/);
  assert.match(client, /injectDeviceManuals/);
  assert.match(client, /augmentBreakdownManualCards/);
  assert.match(client, /attachSingleBreakdownManualTool/);
  assert.match(client, /machineparkOpenManualPdf/);
});

test('PDF kan bewust offline beschikbaar worden gemaakt zonder alle handleidingen te downloaden', () => {
  assert.match(client, /machinepark-manual-files-v1/);
  assert.match(client, /makeManualOffline/);
  assert.match(client, /Offline beschikbaar maken/);
  assert.match(client, /clearOfflineManualVersions/);
  assert.match(client, /navigator\.onLine === false/);
});

test('handleidingen doen mee met build service worker en functiecontrole', () => {
  assert.equal(packageJson.version, '1.68.9');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-library\.py/);
  assert.ok(chain.indexOf('build-fault-cache-online-refresh.py') < chain.indexOf('build-manual-library.py'));
  assert.ok(chain.indexOf('build-manual-library.py') < chain.indexOf('build-offline-first.py'));
  assert.match(packageJson.scripts['check:functions'], /manual-library\.js/);
  assert.match(packageJson.scripts['check:functions'], /netlify\/functions\/manual-library\.mjs/);
  assert.match(build, /'\/manual-library\.js'/);
  assert.match(build, /'\/manual-library\.css'/);
});
