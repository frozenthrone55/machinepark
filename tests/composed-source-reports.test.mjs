import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = path => fs.readFileSync(path, 'utf8');
const patch = read('build-composed-source-reports.py');
const saveFix = read('build-composed-device-selection-save-fix.py');
const pkg = JSON.parse(read('package.json'));

test('verslagtabel staat naast toestellen en gebruikt hetzelfde zoekvak', () => {
  assert.match(patch, /composed-source-grid/);
  assert.match(patch, /Depannages, onderhouden en serviceverslagen/);
  assert.match(patch, /composedFilteredSourceReports/);
  assert.match(patch, /getElementById\('composedDeviceSearch'\)/);
});

test('verslagtabel heeft dezelfde selectieknoppen als toestellentabel', () => {
  assert.match(patch, /<button[^>]*composedSelectVisibleReports[^>]*>Alles zichtbaar aanvinken<\/button>/);
  assert.match(patch, /<button[^>]*composedClearReportSelection[^>]*>Selectie wissen<\/button>/);
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

test('alleen toestel links selecteren blijft voldoende om samengesteld document op te slaan', () => {
  assert.match(patch, /if\(!keys\.size\)return composedBaseSnapshot\(\[\.\.\.fullDeviceIds\]\)/);
  assert.match(patch, /if\(!selectedComposedDevices\.size&&!selectedComposedReports\.size\)/);
  assert.match(saveFix, /composedSyncVisibleDeviceSelection/);
  assert.match(saveFix, /if\(cb\.checked\)selectedComposedDevices\.add\(id\)/);
  assert.match(saveFix, /saveButton\.onclick=\(\)=>saveComposedDocument\(\)/);
});

test('ToDos van gekozen toestellen en gekoppelde serviceverslagen gaan mee in samengesteld document', () => {
  assert.match(saveFix, /composed-todos-v1/);
  assert.match(saveFix, /const actions=\(state\.actions\|\|\[\]\)\.filter/);
  assert.match(saveFix, /fullDeviceIds\.has\(String\(item\.deviceId\|\|''\)\)/);
  assert.match(saveFix, /includedReportIds/);
  assert.match(saveFix, /snapshot\?\.maintenance/);
  assert.match(saveFix, /snapshot\?\.breakdowns/);
  assert.match(saveFix, /record\?\.serviceReportId/);
  assert.match(saveFix, /record\?\.serviceVisitId/);
  assert.match(saveFix, /composedTodoServiceIds\(item\)\.some\(id=>includedReportIds\.has\(id\)\)/);
});

test('ToDos staan chronologisch per locatie in het verslag en houden hun fotos', () => {
  assert.match(saveFix, /composedHistoryRows=function\(snapshot\)/);
  assert.match(saveFix, /kind:'ToDo'/);
  assert.match(saveFix, /composedHistoryEventHtml=function\(snapshot,event\)/);
  assert.match(saveFix, /composedHistoryPhotosHtml\(event\.rows,'ToDo'\)/);
  assert.match(saveFix, /serviceverslagen, ToDo’s/);
});

test('verslagtabel en toestel-opslagfix worden rechtstreeks door npm build uitgevoerd', () => {
  assert.ok(pkg.scripts.build.includes('python3 build-composed-source-reports.py'));
  assert.ok(pkg.scripts.build.indexOf('build-composed-source-reports.py') > pkg.scripts.build.indexOf('build-composed-history-device-photos.py'));
  assert.ok(pkg.scripts.build.includes('python3 build-composed-device-selection-save-fix.py'));
  assert.ok(pkg.scripts.build.indexOf('build-composed-device-selection-save-fix.py') > pkg.scripts.build.indexOf('build-composed-source-reports.py'));
});
