import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-mobile-device-photo-save-reliability.py', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('mobiele toestel-save wacht op lopende fotoverwerking en hergebruikt de eerste submit', () => {
  assert.match(builder, /photoProcessingPromise/);
  assert.match(builder, /event\.preventDefault\(\)/);
  assert.match(builder, /event\.stopImmediatePropagation\(\)/);
  assert.match(builder, /queuedPhotoSubmit/);
  assert.match(builder, /requestSubmit\(usableSubmitter\)/);
  assert.match(builder, /toestel wordt daarna automatisch opgeslagen/);
});

test('foto-hiddenvelden worden ververst voordat de fotoverwerkingspromise klaar is', () => {
  const taskStart = builder.indexOf('const task = (async () => {');
  const renderAt = builder.indexOf('render();', taskStart);
  const promiseAssign = builder.indexOf('photoProcessingPromise = task;', taskStart);
  assert.ok(taskStart >= 0, 'fotoverwerkingstaak moet bestaan');
  assert.ok(renderAt > taskStart, 'render moet binnen de fotoverwerkingstaak gebeuren');
  assert.ok(promiseAssign > renderAt, 'de taak mag pas als pending promise gebruikt worden nadat render in het taakblok zit');
});

test('een fotofout laat het toestel niet stilletjes zonder foto verder opslaan', () => {
  assert.match(builder, /pending\.then\(\(\) =>/);
  assert.match(builder, /\.catch\(\(\) => \{/);
  assert.match(builder, /toestel is nog niet opgeslagen/);
});

test('mobiele fotofix staat direct na toestelfoto-picker en voor uploadlaag in de build', () => {
  const chain = packageJson.scripts.build;
  const photos = chain.indexOf('build-device-photos.py');
  const mobile = chain.indexOf('build-mobile-device-photo-save-reliability.py');
  const blob = chain.indexOf('build-device-photo-blob-storage.py');
  assert.ok(photos >= 0 && mobile > photos, 'mobiele fix moet na de toestelfoto-picker bouwen');
  assert.ok(blob > mobile, 'mobiele fix moet voor de aparte foto-uploadlaag bouwen');
});
