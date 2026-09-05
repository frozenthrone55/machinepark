import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-mill-workorder-times.py', import.meta.url), 'utf8');
const js = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('molengegevens nemen per veld steeds de recentste niet-lege waarde', () => {
  assert.ok(build.includes('latestMillTimesForDevice'));
  assert.ok(build.includes(".sort((a, b) => millRecordSortKey(b).localeCompare(millRecordSortKey(a)))"));
  assert.ok(build.includes("if (!value) return;"));
  assert.ok(build.includes("if (!labelKey || byLabel.has(labelKey)) return;"));
  assert.ok(build.includes('isMillTrackedField'));
});

test('molengegevens herkennen tijden aantallen en maalgraad', () => {
  assert.ok(build.includes('isMillTimeField'));
  assert.ok(build.includes('isMillCountField'));
  assert.ok(build.includes('isMillGrindField'));
  assert.ok(build.includes('aantal|aantallen|count|counts'));
  assert.ok(build.includes('maalgraad|maalstand|maling|grind|grinder setting|grind setting'));
});

test('machinedetails tonen laatste molengegevens met registratiedatum via bestaande detailhook', () => {
  assert.ok(js.includes('Laatste molengegevens'));
  assert.ok(js.includes('Laatst genoteerd op'));
  assert.ok(js.includes('recentste ingevulde waarde per tijd, aantal en maalgraad'));
  assert.ok(js.includes('mill-latest-times-block'));
  assert.ok(js.includes('machineparkInsertMillTimes'));
  assert.doesNotMatch(js, /baseShowDeviceHistoryForMillTimes/);
});

test('nieuwe molenwerkbon toont vorige tijd aantal en maalgraad alleen als lichte referentie', () => {
  assert.ok(js.includes('workorder-last-value-hint'));
  assert.ok(js.includes('Vorige waarde:'));
  assert.ok(js.includes("select.value === '__saved__'"));
  assert.ok(js.includes('data-workorder-field'));
  assert.ok(js.includes('isMillTrackedField'));
  assert.ok(js.includes("name.includes('molen')") || js.includes("text.includes('molen')"));
});

test('molenreferentie zit na werkbondecimale invoer in de build', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-mill-workorder-times.py'));
  assert.ok(script.indexOf('build-work-order-decimals.py') < script.indexOf('build-mill-workorder-times.py'));
  assert.ok(script.indexOf('build-mill-workorder-times.py') < script.indexOf('scripts/extract-build-assets.py'));
});
