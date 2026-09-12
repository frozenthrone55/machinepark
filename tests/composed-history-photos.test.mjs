import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-composed-history-photos.py');
const layout = read('build-composed-layout.py');
const html = read('index.html');
const buildJs = read('assets/machinepark-build.js');
const built = `${html}\n${buildJs}`;

test('samengesteld overzicht bouwt chronologische geschiedenis per locatie van nieuwste naar oudste', () => {
  assert.ok(built.includes('composed-history-photos-v1'));
  assert.ok(built.includes('Chronologische geschiedenis per locatie'));
  assert.ok(patch.includes("events.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')))"));
  assert.ok(patch.includes("sort((a,b)=>String(b.events[0]?.moment||'').localeCompare(String(a.events[0]?.moment||'')))"));
  assert.match(patch, /Locatiewijziging/);
});

test('serviceverslagen groeperen gekoppelde onderhouds depannage en andere registraties zonder dubbele losse weergave', () => {
  assert.match(patch, /record\.serviceVisitId\|\|record\.serviceReportId/);
  assert.match(patch, /kind:'Serviceverslag'/);
  assert.match(patch, /event\.rows\.push\(row\)/);
  assert.match(patch, /serviceKind===['"]other['"]/);
});

test('alle verslagfotos staan bij de juiste gebeurtenis zonder limiet van vijf of tien', () => {
  assert.match(patch, /row\?\.item\?\.photos/);
  assert.match(patch, /data-photo-lightbox/);
  assert.match(patch, /class=\\"composed-history-photo\\"/);
  assert.doesNotMatch(patch, /composedHistoryPhotoList[\s\S]{0,700}\.slice\(0,\s*(5|10)\)/);
  assert.ok(built.includes('Foto’s staan bij het bijbehorende verslag.'));
});

test('afdruk wacht op verslagfotos en samengestelde PDF neemt fotos werkelijk op', () => {
  assert.match(patch, /Promise\.all\(imgs\.map/);
  assert.match(patch, /fetch\(src,\{credentials:'same-origin',cache:'no-store'\}\)/);
  assert.match(patch, /pdf\.addImage\(img\.data,'JPEG'/);
  assert.match(patch, /createComposedPdfFile=async function/);
});

test('geschiedenis-fotopatch wordt automatisch na composed layout gebouwd', () => {
  assert.match(layout, /import runpy/);
  assert.match(layout, /build-composed-history-photos\.py/);
  assert.match(layout, /runpy\.run_path/);
});
