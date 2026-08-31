import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-work-order-decimals.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('werkbon-getalveld gebruikt decimale tekstinvoer in plaats van HTML number', () => {
  assert.match(js, /data-workorder-number=\"1\"/);
  assert.match(js, /inputmode=\"decimal\"/);
  assert.doesNotMatch(js, /field\.type === 'number' \? 'number'/);
});

test('werkbon-getalveld accepteert zowel komma als punt en valideert overige tekst', () => {
  assert.ok(build.includes("(?:\\d+(?:[.,]\\d+)?|[.,]\\d+)"));
  assert.match(js, /bij “\$\{field\.label\}”, bijvoorbeeld 12,5 of 12\.5/);
});

test('decimale werkbonpatch zit na de werkbonplaatsing in de build', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-work-order-decimals.py'));
  assert.ok(script.indexOf('build-work-orders-placement-fix.py') < script.indexOf('build-work-order-decimals.py'));
  assert.ok(script.indexOf('build-work-order-decimals.py') < script.indexOf('scripts/extract-build-assets.py'));
});
