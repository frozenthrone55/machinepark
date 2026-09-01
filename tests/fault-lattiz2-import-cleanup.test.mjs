import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-fault-lattiz2-import-cleanup.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('foutieve Lattiz2 import wordt exact op Lattiz2 gericht verwijderd', () => {
  assert.match(build, /fault-lattiz2-import-cleanup-v1/);
  assert.match(build, /cleanupNorm\(fault\?\.brand\) === 'lattiz2'/);
  assert.match(build, /cleanupNorm\(fault\?\.model\) === 'lattiz2'/);
  assert.match(build, /config\.faults\.filter\(\(fault\) => !isLattiz2ImportedFault\(fault\)\)/);
  assert.match(build, /import volledig verwijderd/);
});

test('Lattiz2 cleanup blijft in de build voor versie 1.68.6', () => {
  assert.equal(packageJson.version, '1.68.6');
  assert.match(packageJson.scripts.build, /build-fault-lattiz2-import-cleanup\.py/);
});
