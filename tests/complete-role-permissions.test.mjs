import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-complete-role-permissions.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const synRole = readFileSync(new URL('../synology/api/_role-lib.php', import.meta.url), 'utf8');
const netPermissions = readFileSync(new URL('../netlify/functions/_shared/permissions.mjs', import.meta.url), 'utf8');
const synData = readFileSync(new URL('../synology/api/machinepark-data.php', import.meta.url), 'utf8');
const actionPhotos = readFileSync(new URL('../synology/api/action-photos.php', import.meta.url), 'utf8');
const synWorkorders = readFileSync(new URL('../synology/api/work-order-templates.php', import.meta.url), 'utf8');
const netWorkorders = readFileSync(new URL('../netlify/functions/work-order-templates.mjs', import.meta.url), 'utf8');
const index = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const buildJs = readFileSync(new URL('../assets/machinepark-build.js', import.meta.url), 'utf8');
const builtUiSource = `${index}\n${buildJs}`;

const newKeys = [
  'view.manuals','manuals.manage','view.actions',
  'actions.add','actions.edit','actions.complete','actions.delete',
  'workorders.manage','mail'
];

test('rollenbeheer bevat alle ontbrekende functies in Synology en Netlify', () => {
  for (const key of newKeys) {
    assert.ok(synRole.includes(key), `Synology mist ${key}`);
    assert.ok(netPermissions.includes(key), `Netlify mist ${key}`);
  }
  assert.match(synRole, /ToDo bekijken/);
  assert.match(synRole, /ToDo toevoegen/);
  assert.match(synRole, /ToDo wijzigen en koppelen/);
  assert.match(synRole, /ToDo-status wijzigen en afronden/);
  assert.match(synRole, /Werkbontemplates beheren/);
  assert.match(synRole, /PDF-verslagen mailen of delen/);
});

test('bestaande standaardrollen behouden hun huidige mogelijkheden bij migratie', () => {
  assert.match(synRole, /strpos\(\$key, 'actions\.'\)/);
  assert.match(synRole, /\$source\['view\.actions'\]/);
  assert.match(synRole, /\$key === 'mail'/);
  assert.match(synRole, /\$source\['print'\]/);
  assert.match(netPermissions, /key\.startsWith\('actions\.'\)/);
  assert.match(netPermissions, /sourcePermissions\['view\.actions'\]/);
  assert.match(netPermissions, /key === 'mail'/);
});

test('ToDo toevoegen wijzigen afronden en verwijderen worden server-side apart gecontroleerd', () => {
  for (const key of ['actions.add','actions.edit','actions.complete','actions.delete']) {
    assert.ok(synData.includes(key), `Synology datavalidatie mist ${key}`);
    assert.ok(netPermissions.includes(key), `Netlify datavalidatie mist ${key}`);
  }
  assert.match(synData, /\$actions = mp_store_diff/);
  assert.match(synData, /\$actionCompletionKeys/);
  assert.match(netPermissions, /const actions = diffList\(before\.actions, after\.actions\)/);
  assert.match(netPermissions, /actionCompletionTriggers/);
});

test('ToDo media volgt wijzigingsrechten in plaats van alleen kijkrecht', () => {
  assert.match(actionPhotos, /\['actions\.add','actions\.edit','actions\.delete'\]/);
  assert.doesNotMatch(actionPhotos, /mp_photo_can\(\$user, \['view\.actions'\]\)/);
});

test('werkbontemplates hebben een configureerbaar recht op beide platformen', () => {
  assert.match(synWorkorders, /permissions\['workorders\.manage'\]/);
  assert.match(netWorkorders, /permissions\?\.\['workorders\.manage'\]/);
  assert.doesNotMatch(synWorkorders, /\(string\)\(\$user\['role'\].*=== 'beheerder'/);
  assert.doesNotMatch(netWorkorders, /access\?\.role === 'beheerder'/);
});

test('ToDo en mail knoppen volgen de nieuwe rechten in de finale UI', () => {
  assert.match(builtUiSource, /machinepark-complete-role-permissions-v1/);
  assert.match(builtUiSource, /machineparkApplyCompleteRolePermissions/);
  assert.match(builtUiSource, /#actionQuickAdd,#actionNewFull/);
  assert.match(builtUiSource, /\[data-action-link\]/);
  assert.match(builtUiSource, /\[data-action-complete\]/);
  assert.match(builtUiSource, /MAIL_SELECTOR/);
  assert.match(builtUiSource, /Deze rol mag geen PDF-verslagen mailen of delen/);
});

test('complete rollenlaag draait na ToDo en video maar voor assetextractie', () => {
  const build = pkg.scripts.build;
  const video = build.indexOf('python3 build-video-media-support.py');
  const complete = build.indexOf('python3 build-complete-role-permissions.py');
  const extract = build.indexOf('python3 scripts/extract-build-assets.py');
  assert.ok(video >= 0 && complete > video, 'complete rollenlaag moet na video/ToDo draaien');
  assert.ok(extract > complete, 'complete rollenlaag moet voor assetextractie draaien');
});

test('builder zelf valideert de volledige permission set', () => {
  for (const key of ['actions.add','actions.edit','actions.complete','actions.delete','workorders.manage','manuals.manage','view.manuals','view.actions']) {
    assert.ok(builder.includes(key), `builder mist ${key}`);
  }
  assert.match(builder, /machineparkApplyCompleteRolePermissions/);
});
