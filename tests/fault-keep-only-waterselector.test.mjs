import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-fault-keep-only-waterselector.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('globale opschoning bewaart uitsluitend de exacte 00005 Waterselector Bravilor Bolero', () => {
  assert.match(build, /fault-keep-only-00005-waterselector-bravilor-bolero-v1/);
  assert.match(build, /cleanupNorm\(fault\?\.name\) === 'waterselector'/);
  assert.match(build, /cleanupNorm\(fault\?\.brand\) === 'bravilor'/);
  assert.match(build, /cleanupNorm\(fault\?\.model\) === 'bolero'/);
  assert.match(build, /\{ version: 1, faults: \[kept\] \}/);
});

test('opschoning verwijdert niets wanneer de exacte keeper ontbreekt', () => {
  assert.match(build, /if \(!kept\)/);
  assert.match(build, /00005 Waterselector · Bravilor · Bolero niet gevonden/);
});

test('eerdere opschoning blijft vóór de definitieve leegmaakactie in de build', () => {
  assert.equal(packageJson.version, '1.68.7');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-fault-keep-only-waterselector\.py/);
  assert.match(chain, /build-fault-clear-all\.py/);
  assert.ok(chain.indexOf('build-fault-lattiz2-import-cleanup.py') < chain.indexOf('build-fault-keep-only-waterselector.py'));
  assert.ok(chain.indexOf('build-fault-keep-only-waterselector.py') < chain.indexOf('build-fault-clear-all.py'));
});
