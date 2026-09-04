import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const patch = readFileSync(new URL('../build-service-draft-cross-device.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('handmatig bewaren en sluiten synchroniseren concept direct centraal', () => {
  assert.match(patch, /syncDraftAcrossDevices/);
  assert.match(patch, /window\.machineparkSyncOnlineNow\(\{ quiet:true \}\)/);
  assert.match(patch, /concept bewaard en gesynchroniseerd/);
  assert.match(patch, /queueDraftSave\(\{ force:true \}\)\.then\(\(\) => syncDraftAcrossDevices\(current\.kind\)\)/);
});

test('verdergaan haalt eerst de nieuwste centrale conceptversie op', () => {
  assert.match(patch, /async function openSavedDraft/);
  assert.match(patch, /pullLatest:true/);
  assert.match(patch, /await refreshDraftState\(kind\)/);
  assert.match(patch, /const header = draftHeader\(kind, id\)/);
});

test('concepten vermelden expliciet dat ze op andere toestellen hervatbaar zijn', () => {
  assert.match(patch, /verdergaan op pc, tablet of gsm/);
});

test('cross-device conceptsync bouwt direct na serviceconcepten en vóór offline-first', () => {
  const chain = packageJson.scripts.build;
  assert.ok(chain.indexOf('build-service-drafts.py') < chain.indexOf('build-service-draft-cross-device.py'));
  assert.ok(chain.indexOf('build-service-draft-cross-device.py') < chain.indexOf('build-offline-first.py'));
  assert.equal(packageJson.version, '1.68.9');
});
