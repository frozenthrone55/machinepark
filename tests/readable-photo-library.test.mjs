import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('Synology fotobibliotheek groepeert per toestel en categorie', () => {
  const builder = readFileSync(new URL('../build-readable-photo-library.py', import.meta.url), 'utf8');
  const api = readFileSync(new URL('../synology/api/photo-library.php', import.meta.url), 'utf8');
  assert.match(builder, /category: 'Toestel'/);
  assert.match(builder, /isService \? 'Service'/);
  assert.match(builder, /'Onderhoud' : 'Depannage'/);
  assert.match(api, /\/volume1\/MachineparkData\/Fotos/);
  assert.match(api, /\['Toestel','Onderhoud','Depannage','Service'\]/);
});

test('leesbare fotobibliotheek synchroniseert verwijderen veilig', () => {
  const api = readFileSync(new URL('../synology/api/photo-library.php', import.meta.url), 'utf8');
  assert.match(api, /glob\(\$dir \. '\/MP_\*'\)/);
  assert.match(api, /isset\(\$desired\[basename\(\$path\)\]\)/);
  assert.match(api, /copy\(\$source,\$tmp\)/);
});

test('fotobibliotheek synchroniseert ook na foto-opslag', () => {
  const builder = readFileSync(new URL('../build-readable-photo-library.py', import.meta.url), 'utf8');
  assert.match(builder, /baseDevicePersist/);
  assert.match(builder, /baseServicePersist/);
  assert.match(builder, /scheduleReadablePhotoLibrary/);
});
