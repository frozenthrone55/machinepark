import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const patch = await readFile(new URL('../build-placement-classification-migration.py', import.meta.url), 'utf8');
const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

test('migratie raakt uitsluitend de drie gevraagde toestellen en exacte plaatsing', () => {
  assert.match(patch, /WCL0685/);
  assert.match(patch, /WCL0678/);
  assert.match(patch, /WCL0684/);
  assert.match(patch, /2026-09-01/);
  assert.match(patch, /15:38/);
  assert.match(patch, /=== 'plaatsing'/);
  assert.match(patch, /candidates\.size !== targetAssets\.size/);
});

test('bestaand record blijft volledig behouden en alleen classificatie wordt toegevoegd', () => {
  assert.match(patch, /return \{ \.\.\.record, serviceKind: 'other', workTypeName: 'Plaatsing' \};/);
  assert.doesNotMatch(patch, /delete record\.photos/);
  assert.doesNotMatch(patch, /delete record\.usedParts/);
  assert.doesNotMatch(patch, /delete record\.oneOffParts/);
  assert.doesNotMatch(patch, /delete record\.workOrder/);
});

test('migratie is eenmalig centraal en wordt voor offline sync gebouwd', () => {
  assert.match(patch, /PLACEMENT_WORKS_MIGRATION_KEY/);
  assert.match(patch, /one-time-migration/);
  assert.match(patch, /await classifySelectedPlacementsOnce\(store, auth\)/);
  const build = pkg.scripts.build;
  const otherWorks = build.indexOf('build-other-works-merged.py');
  const migration = build.indexOf('build-placement-classification-migration.py');
  const offline = build.indexOf('build-offline-first.py');
  assert.ok(otherWorks >= 0 && migration > otherWorks && offline > migration);
  assert.equal(build.split('build-placement-classification-migration.py').length - 1, 1);
  assert.equal(pkg.version, '1.68.9');
});
