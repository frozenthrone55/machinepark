import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const buildJs = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const buildCss = readFileSync(new URL('../assets/machinepark-build.css', import.meta.url), 'utf8');
const source = `${html}\n${buildJs}\n${buildCss}`;

test('lokale toestelmap-import koppelt veilig op toestelnummer of serienummer', () => {
  assert.ok(source.includes('device-photo-folder-import-v1'));
  assert.ok(source.includes("['toestelnummer', lookup.strictAsset, strict]"));
  assert.ok(source.includes("['serienummer', lookup.strictSerial, strict]"));
  assert.ok(source.includes('ambiguous'));
  assert.ok(source.includes('Geen toestel gevonden'));
});

test('map-import overschrijft geen bestaande toestelfotos', () => {
  assert.ok(source.includes("else if (match.device && photos.length) status = 'existing'"));
  assert.ok(source.includes('Bestaande foto’s worden nooit overschreven.'));
  assert.ok(source.includes('if (!device || devicePhotos(device).length)'));
});

test('map-import gebruikt bestaande geoptimaliseerde foto-opslag', () => {
  assert.ok(source.includes('MAX_DEVICE_IMPORT_PHOTOS = 5'));
  assert.ok(source.includes('max = 720'));
  assert.ok(source.includes('window.machineparkPersistDevicePhotoList(device.id, compressed, { force: true })'));
  assert.ok(source.includes('deviceOverviewPhotoIndex: 0'));
  assert.ok(source.includes('await syncBulkImport()'));
});

test('map-import vraagt expliciete browsermap en rechten', () => {
  assert.ok(source.includes('showDirectoryPicker'));
  assert.ok(source.includes('webkitdirectory'));
  assert.ok(source.includes("window.machineparkHasPermission('devices.import')"));
  assert.ok(source.includes("window.machineparkHasPermission('devices.edit')"));
});
