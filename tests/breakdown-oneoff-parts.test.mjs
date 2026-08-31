import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-breakdown-oneoff-parts.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('depannage ondersteunt meerdere eenmalige onderdelen met leveranciercode en omschrijving', () => {
  for (const needle of ['Eenmalige onderdelen','Leveranciercode','Omschrijving','data-add-breakdown-oneoff','breakdown-oneoff-row','LIMIT = 30']) {
    assert.ok(build.includes(needle), `ontbreekt: ${needle}`);
  }
});

test('eenmalige onderdelen worden per depannage en per machine opgeslagen zonder voorraadkoppeling', () => {
  assert.ok(build.includes('oneOffParts:item.oneOffParts'));
  assert.ok(build.includes('oneOffParts:window.machineparkCollectBreakdownOneOff'));
  assert.ok(build.includes("card.querySelector('.breakdown-oneoff-parts')"));
  assert.ok(build.includes('Deze regels wijzigen de voorraad niet.'));
  assert.ok(!build.includes('applyUsage(oneOffParts'));
});

test('eenmalige onderdelen verschijnen in depannagedetails en op de depannage-afdruk', () => {
  assert.ok(build.includes('data-breakdown-oneoff-details'));
  assert.ok(build.includes("=== 'Gebruikte onderdelen'"));
  assert.ok(build.includes('injectOneOffPrint'));
  assert.ok(build.includes('data-print-oneoff-parts'));
  assert.ok(build.includes('service-print-field full'));
});

test('eenmalige onderdelen draaien na depannagedetails en voor assetextractie', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-breakdown-oneoff-parts.py'));
  assert.ok(script.indexOf('build-breakdown-details.py') < script.indexOf('build-breakdown-oneoff-parts.py'));
  assert.ok(script.indexOf('build-breakdown-oneoff-parts.py') < script.indexOf('scripts/extract-build-assets.py'));
});
