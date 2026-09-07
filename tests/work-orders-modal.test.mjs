import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const js = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../assets/machinepark-build.css', import.meta.url), 'utf8');

test('nieuwe werkboneditor verschijnt boven de configuratiepagina', () => {
  assert.match(css, /body\.workorder-config-active \.modal-backdrop\{z-index:2600\}/);
  assert.match(js, /document\.body\.classList\.add\('workorder-config-active'\)/);
  assert.match(js, /document\.body\.classList\.remove\('workorder-config-active'\)/);
  assert.match(js, /newWorkOrderTemplate/);
  assert.match(js, /openTemplateEditor\(\)/);
});
