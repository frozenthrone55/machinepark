import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-breakdown-oneoff-parts.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('eenmalige onderdelen ondersteunen leveranciercode omschrijving en aantal', () => {
  for (const needle of ['Eenmalige onderdelen','Leveranciercode','Omschrijving','Aantal','service-oneoff-qty','data-add-service-oneoff','service-oneoff-row','LIMIT = 30']) {
    assert.ok(build.includes(needle), `ontbreekt: ${needle}`);
  }
  assert.ok(build.includes("qty: Math.max(1"));
  assert.ok(build.includes('`${item.qty} × ${text}`'));
});

test('eenmalige onderdelen worden per depannage en per machine opgeslagen zonder voorraadkoppeling', () => {
  assert.ok(build.includes('oneOffParts:item.oneOffParts'));
  assert.ok(build.includes('machineparkCollectServiceOneOff'));
  assert.ok(build.includes("card.querySelector('.service-oneoff-parts')"));
  assert.ok(build.includes('Deze regels wijzigen de voorraad niet.'));
  assert.ok(!build.includes('applyUsage(oneOffParts'));
});

test('onderhoud ondersteunt dezelfde eenmalige onderdelen per machine en bij bewerken', () => {
  assert.ok(build.includes('maintenance-device-usage-list'));
  assert.ok(build.includes('previousMaintenanceForm'));
  assert.ok(build.includes('previousMaintenanceMachineCardHtml'));
  assert.ok(build.includes('previousSetMaintenanceMachineEnabled'));
  assert.ok(build.includes("kind:'maintenance'"));
  assert.ok(build.includes('oneOffParts:window.machineparkCollectServiceOneOff'));
});

test('eenmalige onderdelen verschijnen in details en afdruk van depannage en onderhoud', () => {
  assert.ok(build.includes('data-breakdown-oneoff-details'));
  assert.ok(build.includes('data-maintenance-oneoff-details'));
  assert.ok(build.includes("=== 'Gebruikte onderdelen'"));
  assert.ok(build.includes('injectOneOffPrint'));
  assert.ok(build.includes('data-print-oneoff-parts'));
  assert.ok(build.includes("kind !== 'breakdowns' && kind !== 'maintenance'"));
});

test('eenmalige onderdelen draaien na depannagedetails en voor assetextractie', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-breakdown-oneoff-parts.py'));
  assert.ok(script.indexOf('build-breakdown-details.py') < script.indexOf('build-breakdown-oneoff-parts.py'));
  assert.ok(script.indexOf('build-breakdown-oneoff-parts.py') < script.indexOf('scripts/extract-build-assets.py'));
});
