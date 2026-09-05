import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-service-oneoff-supplier.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('eenmalige onderdelen krijgen leverancier vóór leveranciercode', () => {
  assert.ok(build.includes('<span>Leverancier</span><span>Leveranciercode</span>'));
  assert.ok(build.includes('class="service-oneoff-supplier"'));
  assert.ok(build.includes('placeholder="Leverancier"'));
});

test('leverancier wordt opgeslagen en verschijnt mee in details en afdruk', () => {
  assert.ok(build.includes("supplier: row.querySelector('.service-oneoff-supplier')?.value || ''"));
  assert.ok(build.includes('[item.supplier, item.supplierCode, item.description]'));
  assert.ok(build.includes("supplier: String(item?.supplier || '').trim().slice(0, 120)"));
});

test('leveranciersveld werkt voor onderhoud en depannage en draait na de eenmalige onderdelenmodule', () => {
  assert.ok(build.includes('leveranciersveld activeren per machine'));
  assert.ok(build.includes('expected, label'));
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-service-oneoff-supplier.py'));
  assert.ok(script.indexOf('build-breakdown-oneoff-parts.py') < script.indexOf('build-service-oneoff-supplier.py'));
  assert.ok(script.indexOf('build-service-oneoff-supplier.py') < script.indexOf('scripts/extract-build-assets.py'));
});
