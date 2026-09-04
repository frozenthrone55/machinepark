import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const root = new URL('../', import.meta.url);
const patch = await readFile(new URL('../build-other-works.py', import.meta.url), 'utf8');
const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

test('Andere werken wordt op dezelfde breakdown-opslag gebouwd met eigen discriminator', () => {
  assert.match(patch, /serviceKind/);
  assert.match(patch, /workTypeName/);
  assert.match(patch, /serviceKind = 'other'/);
  assert.match(patch, /state\.breakdowns/);
});

test('Plaatsing is standaard en nieuwe namen worden uit eerdere registraties hergebruikt', () => {
  assert.match(patch, /const names=\['Plaatsing'\]/);
  assert.match(patch, /Nieuwe naam toevoegen/);
  assert.match(patch, /function typeNames/);
  assert.match(patch, /item\.workTypeName/);
});

test('Andere werken krijgt eigen tab en wordt met gekozen naam in Werkzaamheden getoond', () => {
  assert.match(patch, /view-otherworks/);
  assert.match(patch, /Andere werken registreren/);
  assert.match(patch, /machineparkRenderCombinedWork=renderCombined/);
  assert.match(patch, /other-work-badge/);
  assert.match(patch, /data-other-work-details/);
});

test('Andere werken behoudt concept-, werkbon- en depannageveldenroute', () => {
  assert.match(patch, /isOtherDraftHeader/);
  assert.match(patch, /machineparkPrepareOtherWorkModal/);
  assert.match(patch, /openBreakdown\(\)/);
  assert.match(patch, /header\?\.serviceKind === 'other'/);
});

test('build voert Andere werken exact eenmaal uit en versie blijft 1.68.9', () => {
  const count = pkg.scripts.build.split('build-other-works.py').length - 1;
  assert.equal(count, 1);
  assert.equal(pkg.version, '1.68.9');
});
