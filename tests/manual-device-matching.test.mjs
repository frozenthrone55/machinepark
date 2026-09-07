import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const client = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-manual-device-matching.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('handleidingen herkennen Bravilor modellen wanneer fabrikant ontbreekt in toestelnaam', () => {
  assert.match(client, /machinepark-manual-device-brand-aliases-v1/);
  assert.match(client, /bravilor:\s*\['sego', 'bolero', 'esprecious', 'sprso'\]/);
  assert.match(client, /normalized\.includes\('bravilor'\) \|\| normalized\.includes\('bonamat'\)/);
  assert.match(client, /const hintedBrandMatch/);
});

test('een specifieke modelmatch mag een ontbrekende merknaam opvangen', () => {
  assert.match(client, /modelNeedle\.length >= 4 && modelMatch/);
  assert.doesNotMatch(client, /if \(!brandNeedle \|\| !\(deviceBrand\.includes\(brandNeedle\)/);
});

test('slimme handleidingkoppeling staat direct na de handleidingenbasis in de build', () => {
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-manual-device-matching\.py/);
  assert.ok(chain.indexOf('build-manual-library.py') < chain.indexOf('build-manual-device-matching.py'));
  assert.ok(chain.indexOf('build-manual-device-matching.py') < chain.indexOf('build-manual-chunk-upload.py'));
  assert.match(build, /Sego/);
});
