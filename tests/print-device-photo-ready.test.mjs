import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-print-device-photo-ready.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('toestelfoto wordt volledig geladen en gedecodeerd voor print', () => {
  assert.match(build, /machinepark-print-device-photo-ready-v1/);
  assert.match(build, /img\.naturalWidth/);
  assert.match(build, /typeof img\.decode === 'function'/);
  assert.match(build, /setTimeout\(done, 7000\)/);
  assert.match(build, /requestAnimationFrame\(\(\) => view\.requestAnimationFrame\(resolve\)\)/);
});

test('afdrukfoto-fix zit na de bestaande toestelfoto- en printbuilds', () => {
  assert.equal(packageJson.version, '1.68.8');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-print-device-photo-ready\.py/);
  assert.ok(chain.indexOf('build-print-device-details.py') < chain.indexOf('build-print-device-photo-ready.py'));
  assert.ok(chain.indexOf('build-photo-storage-optimization.py') < chain.indexOf('build-print-device-photo-ready.py'));
});
