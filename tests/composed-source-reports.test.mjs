import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-composed-source-reports.py');
const pkg = JSON.parse(read('package.json'));

test('verslagtabel staat naast toestellen en gebruikt hetzelfde zoekvak', () => {
  assert.match(patch, /composed-source-grid/);
  assert.match(patch, /Depannages, onderhouden en serviceverslagen/);
  assert.match(patch, /composedFilteredSourceReports/);
  assert.match(patch, /getElementById\('composedDeviceSearch'\)/);
});

test('verslagtabel heeft dezelfde selectieknoppen als toestellentabel', () => {
  assert.match(patch, /<button[^>]*composedSelectVisibleReports[^>]*button[^>]*>Alles zichtbaar aanvinken<\/button>/);
  assert.match(patch, /<button[^>]*composedClearReportSelection[^>]*button[^>]*>Selectie wissen<\/button>/);
  assert.doesNotMatch(patch, /<input[^>]*composedSelectVisibleReports/);
  assert.doesNotMatch(patch, /<input[^>]*composedClearReportSelection/);
});

test('specifiek geselecteerde verslagen worden werkelijk in snapshot opgenomen', () => {
  assert.match(patch, /selectedComposedReports=new Set/);
  assert.match(patch, /composedSnapshot=function\(deviceIds,reportKeys=/);
  assert.match(patch, /selectedMaintenance/);
  assert.match(patch, /selectedBreakdowns/);
  assert.match(patch, /Vink minstens één toestel of verslag aan/);
});

test('verslagtabel wordt rechtstreeks door npm build uitgevoerd', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-composed-source-reports.py'));
  assert.ok(pkg.scripts.build.indexOf('build-composed-source-reports.py') > pkg.scripts.build.indexOf('build-composed-history-device-photos.py'));
});
