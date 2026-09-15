import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const actionsBuilder = readFileSync(new URL('../build-actions.py', import.meta.url), 'utf8');
const autoLiveBuilder = readFileSync(new URL('../build-auto-live-sync.py', import.meta.url), 'utf8');
const syncBuilder = readFileSync(new URL('../build-sync-drift-recovery.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('alle centrale Machinepark-stores krijgen snelle write-bevestiging', () => {
  // De regressietests draaien na npm run build. Op dat moment heeft build-actions.py
  // de uiteindelijke centrale storelijst al uitgebreid met actions.
  assert.match(index, /const stores=\['parts','devices','maintenance','breakdowns','actions'\]/);
  assert.match(actionsBuilder, /const stores=\['parts','devices','maintenance','breakdowns','actions'\]/);
  assert.match(autoLiveBuilder, /machinepark-core-store-fast-sync-v1/);

  for (const store of ['maintenance', 'breakdowns', 'devices', 'parts', 'actions']) {
    assert.match(autoLiveBuilder, new RegExp(`storeName !== '${store}'`), `${store} moet in de snelle sync-route zitten`);
  }

  assert.match(syncBuilder, /put = async function\(storeName, item\)/);
  assert.match(syncBuilder, /putMany = async function\(storeName, items\)/);
  assert.match(syncBuilder, /queueServiceWriteSync\(storeName\)/);
});

test('losse onderdeelwijzigingen lopen door dezelfde beschermde put-route', () => {
  const start = index.indexOf('function openPart(id)');
  const end = index.indexOf('function deviceForm', start);
  assert.ok(start >= 0 && end > start, 'openPart-opslagblok moet vindbaar zijn');
  const block = index.slice(start, end);
  assert.match(block, /await put\('parts',obj\)/);
  assert.match(block, /stock:Number\(fd\.get\('stock'\)\|\|0\)/);
  assert.match(block, /minStock:Number\(fd\.get\('minStock'\)\|\|0\)/);
  assert.match(block, /price:Number\(fd\.get\('price'\)\|\|0\)/);
});

test('actie toevoegen, wijzigen, afronden en heropenen lopen door de beschermde put-route', () => {
  assert.match(actionsBuilder, /await put\('actions',obj\)/);
  assert.match(actionsBuilder, /await put\('actions',updated\)/);
  assert.match(actionsBuilder, /async function quickAddAction\(\)/);
  assert.match(actionsBuilder, /async function openCompleteAction\(id\)/);
  assert.match(actionsBuilder, /async function reopenAction\(id\)/);
  assert.match(actionsBuilder, /pushActionDeletionNow/);
});

test('snelle core-sync wordt gebouwd na driftbescherming en voor asset-extractie', () => {
  const chain = packageJson.scripts.build;
  assert.ok(chain.indexOf('build-sync-drift-recovery.py') < chain.indexOf('build-auto-live-sync.py'));
  assert.ok(chain.indexOf('build-auto-live-sync.py') < chain.indexOf('scripts/extract-build-assets.py'));
  assert.ok(chain.indexOf('build-actions.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
