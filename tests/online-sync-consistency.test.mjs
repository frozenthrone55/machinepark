import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-online-sync-consistency.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('remote/local merge wordt na succesvolle push meteen lokaal toegepast', () => {
  assert.match(build, /let reconciledRemote = false/);
  assert.match(build, /reconciledRemote = true/);
  assert.match(build, /await replaceLocalSnapshot\(local\)/);
  assert.match(build, /await refresh\(\)/);
});

test('bij serviceconflicten wint de nieuwste onderhouds- of depannageversie', () => {
  assert.match(build, /function serviceSyncTime\(item\)/);
  assert.match(build, /function preferRemoteServiceConflict\(storeName, local, remote\)/);
  assert.match(build, /storeName !== 'maintenance' && storeName !== 'breakdowns'/);
  assert.match(build, /remoteTime >= localTime/);
  assert.match(build, /preferRemoteServiceConflict\(storeName, local, remote\)/);
});

test('alleen offline gaan markeert de dataset niet als gewijzigd', () => {
  assert.match(build, /window\.addEventListener\('offline'/);
  assert.match(build, /offline gaan markeert nog steeds onterecht/);
});

test('online app ververst hoofddata storingen en werkbonnen direct', () => {
  assert.match(build, /async function syncOnlineNow/);
  assert.match(build, /await centralPull\(\{ apply: true, quiet: true \}\)/);
  assert.match(build, /machineparkLoadFaultLibrary\(true\)/);
  assert.match(build, /machineparkLoadWorkOrderTemplates\(true\)/);
});

test('focus en terugkeren naar zichtbare tab starten directe online sync', () => {
  assert.match(build, /window\.addEventListener\('focus', scheduleImmediateOnlineSync\)/);
  assert.match(build, /document\.addEventListener\('visibilitychange'/);
  assert.match(build, /document\.visibilityState === 'visible'/);
});

test('versie 1.68.7 bouwt de consistente online sync als laatste offline patch', () => {
  assert.equal(packageJson.version, '1.68.7');
  const chain = packageJson.scripts.build;
  assert.match(chain, /build-online-sync-consistency\.py/);
  assert.ok(chain.indexOf('build-central-access-etag.py') < chain.indexOf('build-online-sync-consistency.py'));
  assert.ok(chain.indexOf('build-online-sync-consistency.py') < chain.indexOf('scripts/extract-build-assets.py'));
});
