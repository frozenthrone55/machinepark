import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-device-out-of-service-row.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('buiten-dienst toestel krijgt een klasse op de volledige tabelrij', () => {
  assert.match(build, /d\.status==='Buiten dienst'\?'device-row-out-of-service':''/);
  assert.match(build, /data-device-history/);
});

test('alle cellen van de buiten-dienst rij krijgen rode styling en hover blijft rood', () => {
  assert.match(build, /\.device-table tr\.device-row-out-of-service td/);
  assert.match(build, /background:#f8dada/);
  assert.match(build, /\.device-table tr\.device-row-out-of-service:hover td/);
  assert.match(build, /background:#f3cccc/);
});

test('versie 1.68.10 bouwt de buiten-dienst rijstijl vóór assetextractie', () => {
  assert.equal(packageJson.version, '1.68.10');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-device-out-of-service-row\.py/);
  assert.ok(chain.indexOf('build-device-out-of-service-row.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
