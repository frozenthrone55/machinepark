import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const build = readFileSync(new URL('../build-device-sync-skip-lines.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('toestelsynchronisatie krijgt per geplande regel een overslaan-vinkje', () => {
  assert.ok(build.includes('device-sync-skip'));
  assert.ok(build.includes('Overslaan'));
  assert.ok(build.includes('data-sync-key'));
  assert.ok(build.includes('device-sync-change-row'));
});

test('aangevinkte synchronisatieregels worden niet verwerkt', () => {
  assert.ok(build.includes('skippedKeys'));
  assert.ok(build.includes('activeAdds:adds.filter'));
  assert.ok(build.includes('activeUpdates:updates.filter'));
  assert.ok(build.includes('for(const r of activeAdds)'));
  assert.ok(build.includes('for(const r of activeUpdates)'));
});

test('synchronisatie toont alle geplande wijzigingen en werkt tellers dynamisch bij', () => {
  assert.ok(build.includes('const rows=changes.map'));
  assert.ok(!build.includes('preview=[...updates,...adds].slice(0,35)'));
  assert.ok(build.includes('updateSelectionSummary'));
  assert.ok(build.includes('deviceSyncSkipCount'));
  assert.ok(build.includes('Niets te verwerken'));
});

test('overslaan-patch draait vroeg in de build voor overige uitbreidingen', () => {
  const script = packageJson.scripts.build;
  assert.ok(script.includes('python3 build-device-sync-skip-lines.py'));
  assert.ok(script.indexOf('build-existing-location-picker.py') < script.indexOf('build-device-sync-skip-lines.py'));
  assert.ok(script.indexOf('build-device-sync-skip-lines.py') < script.indexOf('scripts/extract-build-assets.py'));
});
