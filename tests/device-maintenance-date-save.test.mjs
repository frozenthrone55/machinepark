import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const autoLiveBuilder = readFileSync(new URL('../build-auto-live-sync.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('toestelformulier bevat halfjaarlijkse en jaarlijkse onderhoudsdatum', () => {
  assert.match(index, /name="nextHalf" type="date"/);
  assert.match(index, /name="nextAnnual" type="date"/);
});

test('een enkele toestel-save bewaart beide onderhoudsdatums in hetzelfde device-object', () => {
  const start = index.indexOf('function openDevice(id)');
  const end = index.indexOf('function usagePartDisplay', start);
  assert.ok(start >= 0 && end > start, 'openDevice-opslagblok moet vindbaar zijn');
  const block = index.slice(start, end);

  assert.match(block, /nextHalf:val\(fd,'nextHalf'\)/);
  assert.match(block, /nextAnnual:val\(fd,'nextAnnual'\)/);
  assert.match(block, /await put\('devices',obj\)/);
  assert.equal((block.match(/await put\('devices',obj\)/g) || []).length, 1);
});

test('device-writes krijgen dezelfde snelle centrale bevestiging als onderhoud en depannages', () => {
  assert.match(autoLiveBuilder, /machinepark-device-write-fast-sync-v1/);
  assert.match(autoLiveBuilder, /storeName !== 'maintenance' && storeName !== 'breakdowns' && storeName !== 'devices'/);
  assert.match(autoLiveBuilder, /queueServiceWriteSync\(storeName\)/);

  const chain = packageJson.scripts.build;
  assert.ok(chain.indexOf('build-sync-drift-recovery.py') < chain.indexOf('build-auto-live-sync.py'));
  assert.ok(chain.indexOf('build-auto-live-sync.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
