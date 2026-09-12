import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-composed-history-device-photos.py');
const pkg = JSON.parse(read('package.json'));
const html = read('index.html');
const buildJs = read('assets/machinepark-build.js');
const built = `${html}\n${buildJs}`;

test('samengesteld verslag houdt fotos bij het juiste toestelblok', () => {
  assert.ok(built.includes('composed-history-device-photos-v1'));
  assert.match(patch, /composedHistoryPhotosHtml\(\[row\]/);
  assert.match(patch, /\$\{parts\?[\s\S]*\$\{photos\}<\/div>/);
});

test('serviceverslag toont geen gezamenlijke fotogalerij meer na alle toestellen', () => {
  assert.match(patch, /const details=rows\.length\?rows\.map\(row=>composedHistoryWorkHtml\(snapshot,row\)\)\.join/);
  assert.match(patch, /\$\{details\}<\/article>/);
  assert.doesNotMatch(patch, /composedHistoryEventHtml[\s\S]{0,900}composedHistoryPhotosHtml\(rows/);
});

test('samengestelde PDF plaatst fotos onmiddellijk na het bijbehorende toestel', () => {
  assert.match(patch, /for\(const row of event\.rows\)[\s\S]{0,900}await addPhotos\(composedHistoryPhotoList\(\[row\]\)\);/);
  assert.doesNotMatch(patch, /await addPhotos\(composedHistoryPhotoList\(event\.rows\)\)/);
});

test('toestel-fotokoppeling draait automatisch in de build', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-composed-history-device-photos.py'));
  assert.ok(pkg.scripts.build.indexOf('build-composed-history-device-photos.py') > pkg.scripts.build.indexOf('build-composed-history-photos.py'));
});
