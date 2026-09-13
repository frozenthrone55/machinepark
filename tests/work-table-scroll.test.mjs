import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-work-table-scroll.py');
const pkg = JSON.parse(read('package.json'));

test('de twee grote tabellen in Werkzaamheden hebben elk een eigen verticale scrollbar', () => {
  assert.match(patch, /#view-work #serviceVisitPanel > \.table-wrap/);
  assert.match(patch, /#view-work \.work-overview-panel \.work-overview-table-wrap/);
  assert.match(patch, /max-height:clamp\(320px,52vh,560px\)/);
  assert.match(patch, /overflow:auto/);
  assert.match(patch, /overscroll-behavior:contain/);
  assert.match(patch, /scrollbar-gutter:stable/);
});

test('kolomkoppen blijven zichtbaar terwijl beide tabellen scrollen', () => {
  assert.match(patch, /position:sticky/);
  assert.match(patch, /top:0/);
  assert.match(patch, /z-index:3/);
});

test('mobiel beperkt beide tabellen eveneens in hoogte', () => {
  assert.match(patch, /@media\(max-width:700px\)/);
  assert.match(patch, /max-height:50vh/);
});

test('scrollfix wordt na service-overzicht en uniforme werk-layout gebouwd', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-work-table-scroll.py'));
  assert.ok(pkg.scripts.build.indexOf('build-work-table-scroll.py') > pkg.scripts.build.indexOf('build-unified-work-layout.py'));
  assert.ok(pkg.scripts.build.indexOf('build-work-table-scroll.py') > pkg.scripts.build.indexOf('build-service-overview-search.py'));
});
