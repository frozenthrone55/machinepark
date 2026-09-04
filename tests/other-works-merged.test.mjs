import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const patch = await readFile(new URL('../build-other-works-merged.py', import.meta.url), 'utf8');
const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'));

test('Andere werken heeft geen apart tabblad meer', () => {
  assert.match(patch, /otherNav=document\.createElement\('button'\)/);
  assert.match(patch, /otherView\.id='view-otherworks'/);
  assert.match(patch, /for forbidden in/);
});

test('Werkzaamheden krijgt een derde registratieknop voor Andere werken', () => {
  assert.match(patch, /id="workAddOtherWork"/);
  assert.match(patch, /\+ Andere werken registreren/);
  assert.match(patch, /addOtherWork\.onclick=\(\)=>openOtherWork\(\)/);
});

test('Andere werken blijft als filter en gekozen werknaam in gezamenlijke historiek', () => {
  assert.match(patch, /option value=\\"otherworks\\"/);
  assert.match(patch, /renderDrafts\(\);renderCombined\(\)/);
  assert.match(patch, /Onderhoud, depannages en andere werken in één chronologische historiek/);
});

test('oude otherworks-route gaat voortaan naar Werkzaamheden', () => {
  assert.match(patch, /view==='otherworks'\?'work':view/);
});

test('samengevoegde patch draait direct na basis Andere werken en voor offline-first', () => {
  const build = pkg.scripts.build;
  const base = build.indexOf('build-other-works.py');
  const merged = build.indexOf('build-other-works-merged.py');
  const offline = build.indexOf('build-offline-first.py');
  assert.ok(base >= 0 && merged > base && offline > merged);
  assert.equal(build.split('build-other-works-merged.py').length - 1, 1);
  assert.equal(pkg.version, '1.68.9');
});
