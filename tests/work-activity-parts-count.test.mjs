import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-work-activity-parts-count.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('Werkzaamheden toont alleen een getal in de kolom Onderdelen', () => {
  assert.match(patch, /function workPartsCount\(item\)/);
  assert.match(patch, /class=\"work-parts-count\"/);
  assert.match(patch, /workPartsCount\(item\)/);
  assert.doesNotMatch(patch, /class=\"work-parts-count\">\$\{esc\(usedPartsText/);
});

test('onderdelenaantal telt voorraadonderdelen en eenmalige onderdelen samen', () => {
  assert.match(patch, /total\(item\?\.usedParts\) \+ total\(item\?\.oneOffParts\)/);
  assert.match(patch, /Number\(part\?\.qty \|\| 0\)/);
});

test('compact onderdelenaantal bouwt direct na Werkzaamheden', () => {
  const chain = packageJson.scripts.build;
  assert.equal(packageJson.version, '1.68.9');
  assert.ok(chain.indexOf('build-work-activities.py') < chain.indexOf('build-work-activity-parts-count.py'));
  assert.ok(chain.indexOf('build-work-activity-parts-count.py') < chain.indexOf('build-offline-first.py'));
});
