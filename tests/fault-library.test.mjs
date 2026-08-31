import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const faultJs = readFileSync(new URL('../fault-library.js', import.meta.url), 'utf8');
const builtSource = `${html}\n${faultJs}`;
const endpoint = readFileSync(new URL('../netlify/functions/fault-library.mjs', import.meta.url), 'utf8');
const permissions = readFileSync(new URL('../netlify/functions/_shared/permissions.mjs', import.meta.url), 'utf8');
const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const sw = readFileSync(new URL('../sw.js', import.meta.url), 'utf8');

test('storingsbibliotheek ondersteunt storingen met en zonder code', () => {
  assert.match(builtSource, /Storingscode \/ nummer/);
  assert.match(builtSource, /code: val\(fd, 'code'\)/);
  assert.match(endpoint, /code: cleanText\(fault\?\.code/);
  assert.match(endpoint, /if \(!name\).*Geef de storing een naam/);
});

test('storingen kunnen algemeen, merk- of modelgebonden zijn', () => {
  assert.match(endpoint, /if \(brand && model\) return 'model'/);
  assert.match(endpoint, /if \(brand\) return 'brand'/);
  assert.match(endpoint, /return 'general'/);
  assert.match(builtSource, /Algemeen · alle merken/);
  assert.match(builtSource, /alle modellen/);
  assert.match(builtSource, /faultAppliesToDevice/);
});

test('storingskennis bevat symptomen oorzaken oplossingen en opmerkingen', () => {
  for (const needle of ['symptoms', 'causes', 'solutions', 'notes']) {
    assert.ok(endpoint.includes(needle), `Ontbrekend storingsveld: ${needle}`);
  }
  assert.match(builtSource, /Mogelijke oorzaken/);
  assert.match(builtSource, /Controle \/ oplossingen/);
});

test('storingsbibliotheek is gekoppeld aan depannages met een momentopname', () => {
  assert.match(builtSource, /faultRef/);
  assert.match(builtSource, /capturedAt: new Date\(\)\.toISOString\(\)/);
  assert.match(builtSource, /storeName === 'breakdowns'/);
  assert.match(builtSource, /Storingsbibliotheek/);
  assert.match(builtSource, /data-fault-pick/);
});

test('storingsbibliotheek is offline leesbaar en runtimebestanden zitten in de service-worker cache', () => {
  assert.match(builtSource, /MachineparkFaultLibraryDB/);
  assert.match(builtSource, /navigator\.onLine === false/);
  assert.match(builtSource, /offline opgeslagen bibliotheek/);
  assert.match(sw, /'\/fault-library\.js'/);
  assert.match(sw, /'\/fault-library\.css'/);
});

test('rollen hebben aparte rechten voor storingen en bestaande ingebouwde rollen migreren veilig', () => {
  assert.match(permissions, /view\.faults/);
  assert.match(permissions, /faults\.manage/);
  assert.match(permissions, /Object\.prototype\.hasOwnProperty\.call\(sourcePermissions, key\)/);
  assert.match(permissions, /existing\?\.builtIn && existing\?\.permissions\?\.\[key\]/);
});

test('build en functiecontrole nemen de storingsbibliotheek mee', () => {
  assert.equal(packageJson.version, '1.67.4');
  assert.match(packageJson.scripts.build, /build-fault-library\.py/);
  assert.match(packageJson.scripts['check:functions'], /fault-library\.mjs/);
});
