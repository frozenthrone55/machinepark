import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import vm from 'node:vm';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const buildJs = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const buildCss = readFileSync(new URL('../assets/machinepark-build.css', import.meta.url), 'utf8');
const builtSource = `${html}\n${buildJs}\n${buildCss}`;
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const version = String(pkg.version || '1');
const escapedVersion = version.replace(/\./g, '\\.');

test('kritieke UI bouwstenen zijn aanwezig', () => {
  for (const needle of [
    '<title>Machinepark</title>',
    'class="device-nav-icon-svg"',
    'stroke:#fff',
    '<span class="dot"></span><div class="label">Actieve toestellen</div>',
    'data-view="maintenance"',
    "$('#addMaintenance').onclick=()=>openMaintenance();",
    'id="maintenanceLocationSearch"',
    'id="maintenanceLocationSuggestions"',
    'maintenanceLocationMatches',
    'locationGroupMatches',
    'locationGroupMatchHint',
    'Typ locatie of toestelnummer…',
    'maintenance-machine-card',
    'maintenanceBatchSelectedItems',
    'data-view="breakdowns"',
    'id="breakdownLocationSearch"',
    'id="breakdownLocationSuggestions"',
    'breakdownLocationMatches',
    'breakdownBatchSelectedItems',
    'deleteServiceRecordAtomic',
    "deleteServiceRecord('maintenance',id)",
    "deleteServiceRecord('breakdowns',old.id)",
    'Alle gebruikte onderdelen van deze registratie worden automatisch terug op voorraad gezet.',
    'data-view="parts"',
    'usage-autocomplete',
    'device-autocomplete',
    'data-undo-audit',
    'id="auditPartsLogBody"',
    'Overige wijzigingen',
    'dashboardProfessional',
    'downloadStockImportReport',
    'makeStoreZip',
    'Afbeelding bestand',
    'afbeeldingen/',
    'backupVersion:3',
    'includesImages:true',
    'countEmbeddedPartImages',
    'Machinepark_Veiligheidsbackup_',
    'Prijs excl. BTW',
    'Op afroep',
    'Maandelijks',
    'technieker',
    'magazijnier',
    'machineparkPersistServicePhotos',
    'machineparkServiceBlobWritesEnabled',
    "host.startsWith('deploy-preview-')",
    'const DEVICE_PHOTO_LIMIT = 5;',
  ]) assert.ok(builtSource.includes(needle), `Ontbreekt in gebouwde app: ${needle}`);
});

test('inline en gegenereerde app-JavaScript bevatten geen syntaxfouten', () => {
  const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1]);
  assert.ok(scripts.length > 0, 'Geen inline scripts gevonden');
  scripts.forEach((code, index) => {
    try {
      new vm.Script(code, { filename: `index-inline-${index + 1}.js` });
    } catch (error) {
      assert.fail(`Syntaxfout in inline script ${index + 1}:\n${error.stack || error.message}`);
    }
  });
  try {
    new vm.Script(buildJs, { filename: 'assets/machinepark-build.js' });
  } catch (error) {
    assert.fail(`Syntaxfout in gegenereerde frontend-JavaScript:\n${error.stack || error.message}`);
  }
});

test('gegenereerde featurecode staat in externe assets', () => {
  assert.ok(html.includes('data-machinepark-generated-asset="css"'));
  assert.ok(html.includes('data-machinepark-generated-asset="js"'));
  assert.ok(html.includes('/assets/machinepark-build.css'));
  assert.ok(html.includes('/assets/machinepark-build.js'));
  assert.ok(buildJs.length > 1000, 'Gegenereerde JavaScript-bundel is onverwacht leeg');
  assert.ok(buildCss.length > 1000, 'Gegenereerde CSS-bundel is onverwacht leeg');
  assert.equal(/<script\b[^>]*data-machinepark-build-fix=/i.test(html), false);
  assert.equal(/<style\b[^>]*data-machinepark-build-fix=/i.test(html), false);
});

test('featureblokken blijven runtime-foutgeisoleerd na bundeling', () => {
  assert.ok(buildJs.includes("console.error('[Machinepark feature "));
  assert.ok(buildJs.includes('/* photo-lightbox-v2 */'));
  assert.ok(buildJs.includes('window.machineparkOpenPhotoLightbox = openPhotoLightbox;'));
  assert.ok(buildJs.includes("event.target.closest('img[data-photo-lightbox]')"));
  assert.ok(builtSource.includes('data-photo-lightbox'));
});

test('frontend-assets gebruiken inhoudsgebonden cache-busting', () => {
  const jsMatch = html.match(new RegExp(`/assets/machinepark-build\\.js\\?v=${escapedVersion}-([a-f0-9]{12})`));
  const cssMatch = html.match(new RegExp(`/assets/machinepark-build\\.css\\?v=${escapedVersion}-([a-f0-9]{12})`));
  assert.ok(jsMatch, 'JavaScript asset mist inhoudshash');
  assert.ok(cssMatch, 'CSS asset mist inhoudshash');
  assert.equal(jsMatch[1], cssMatch[1], 'JS en CSS moeten dezelfde buildhash gebruiken');
  assert.ok(sw.includes(`machinepark-v${version}-assets-${jsMatch[1]}`));
  assert.ok(sw.includes(`/assets/machinepark-build.js?v=${version}-${jsMatch[1]}`));
  assert.ok(sw.includes(`/assets/machinepark-build.css?v=${version}-${jsMatch[1]}`));
});

test('Clerk profielknop is uniek en gevaarlijke alles-wissen actie is weg', () => {
  assert.equal((html.match(/id="clerkUserButton"/g) || []).length, 1);
  assert.equal(html.includes('id="clearAll"'), false);
});

test('service worker cachet de modulaire frontend-assets', () => {
  assert.ok(sw.includes(`machinepark-v${version}-assets-`));
  assert.ok(sw.includes('/assets/machinepark-build.js'));
  assert.ok(sw.includes('/assets/machinepark-build.css'));
  assert.ok(sw.includes('/offline-first.js'));
});

test('scriptsmap bevat alleen de vaste build-, audit- en finalizetooling', () => {
  const scripts = readdirSync(new URL('../scripts/', import.meta.url)).sort();
  assert.deepEqual(scripts, ['audit-codebase.py', 'build-machinepark.py', 'extract-build-assets.py']);
});
