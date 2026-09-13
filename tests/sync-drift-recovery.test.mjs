import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-sync-drift-recovery.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('lokale IndexedDB-afwijkingen worden herkend ook zonder dirty-vlag', () => {
  assert.match(build, /function snapshotStoresEqual\(a, b\)/);
  assert.match(build, /Boolean\(meta\.base\) && !snapshotStoresEqual\(meta\.base, localBeforePull\)/);
  assert.match(build, /if \(localDrift && !meta\.dirty\)/);
  assert.match(build, /centralSync\.offlineDirty = true/);
});

test('lokale writes krijgen een synchrone herstelhint en oplopende writeteller', () => {
  assert.match(build, /machinepark-local-write-pending-v1/);
  assert.match(build, /machinepark-new-entry-race-v1/);
  assert.match(build, /function localWriteSequence\(\)/);
  assert.match(build, /function noteLocalWrite\(\)/);
  assert.match(build, /noteLocalWrite\(\);[\s\S]{0,220}markPendingLocalWriteHint\(\)/);
  assert.match(build, /hasPendingLocalWriteHint\(\)/);
  assert.match(build, /clearPendingLocalWriteHint\(\)/);
});

test('lopende pull mag een invoer die tijdens de GET ontstaat niet overschrijven', () => {
  assert.match(build, /const pullWriteSequence = localWriteSequence\(\)/);
  assert.match(build, /const pullLocalBaseline = await localSnapshot\(\)/);
  assert.match(build, /const localBeforeApply = await localSnapshot\(\)/);
  assert.match(build, /!snapshotStoresEqual\(pullLocalBaseline, localBeforeApply\)/);
  assert.match(build, /localWriteSequence\(\) !== pullWriteSequence/);
  assert.match(build, /skippedApply: true/);
  assert.match(build, /Nieuwe invoer lokaal bewaard · synchronisatie volgt/);
});

test('lopende push markeert een later opgeslagen invoer niet ten onrechte als schoon', () => {
  assert.match(build, /const pushWriteSequence = localWriteSequence\(\)/);
  assert.match(build, /const pushStartedLocal = local/);
  assert.match(build, /const localAfterPush = await localSnapshot\(\)/);
  assert.match(build, /const newerLocalWrite = localWriteSequence\(\) !== pushWriteSequence/);
  assert.match(build, /retryEtag = reconciledRemote/);
  assert.match(build, /retryBase = reconciledRemote \? pushStartedLocal : local/);
  assert.match(build, /dirty: true/);
  assert.match(build, /pending: true/);
});

test('onderhoud en depannages krijgen een snelle centrale sync-trigger', () => {
  assert.match(build, /storeName !== 'maintenance' && storeName !== 'breakdowns'/);
  assert.match(build, /queueServiceWriteSync\(storeName\)/);
  assert.match(build, /baseServicePutMany/);
  assert.match(build, /baseDeleteServiceRecordAtomic/);
  assert.match(build, /Registratie centraal bevestigen/);
});

test('drift-herstel draait na de algemene online consistency patch', () => {
  assert.equal(packageJson.version, '1.68.10');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-sync-drift-recovery\.py/);
  assert.ok(chain.indexOf('build-online-sync-consistency.py') < chain.indexOf('build-sync-drift-recovery.py'));
  assert.ok(chain.indexOf('build-sync-drift-recovery.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
