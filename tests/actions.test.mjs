import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const builder = readFileSync(new URL('../build-actions.py', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));
const nav = readFileSync(new URL('../build-navigation-runtime.py', import.meta.url), 'utf8');
const service = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const dataApi = readFileSync(new URL('../synology/api/machinepark-data.php', import.meta.url), 'utf8');
const userApi = readFileSync(new URL('../synology/api/action-users.php', import.meta.url), 'utf8');
const auditLib = readFileSync(new URL('../synology/api/_audit-lib.php', import.meta.url), 'utf8');
const auditLog = readFileSync(new URL('../synology/api/audit-log.php', import.meta.url), 'utf8');
const roleLib = readFileSync(new URL('../synology/api/_role-lib.php', import.meta.url), 'utf8');

test('Acties is een eigen offline datastore met DB-migratie', () => {
  assert.match(builder, /DB_VERSION=2/);
  assert.match(builder, /breakdowns','actions/);
  assert.match(builder, /actions:\\[\\]/);
  assert.match(builder, /put\\('actions'/);
});

test('Acties heeft twee lijsten, snel toevoegen en afronden', () => {
  assert.match(builder, /Nog te doen/);
  assert.match(builder, /Uitgevoerd/);
  assert.match(builder, /actionQuickInput/);
  assert.match(builder, /quickAddAction/);
  assert.match(builder, /openCompleteAction/);
  assert.match(builder, /completedByName/);
  assert.match(builder, /30\\*86400000/);
  assert.match(builder, /reopenAction/);
});

test('Acties ondersteunt gebruiker toestel context en historiek', () => {
  assert.match(builder, /action-users\\.php/);
  assert.match(builder, /assigneeName/);
  assert.match(builder, /actionDeviceSearchField/);
  assert.match(builder, /historyEntry/);
  assert.match(builder, /decorateDeviceModal/);
  assert.match(builder, /decorateContextModal\\('maintenance'/);
  assert.match(builder, /decorateContextModal\\('breakdown'/);
  assert.match(service, /machineparkDecorateServiceReportActions/);
});

test('Acties verschijnt op dashboard en navigatie', () => {
  assert.match(builder, /kpiActions/);
  assert.match(builder, /actionNavCount/);
  assert.match(nav, /actions: \\['Acties'/);
  assert.match(nav, /machineparkRenderActions/);
});

test('Acties bouwt als laatste feature voor assetextractie', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-actions.py'));
  assert.ok(cmd.indexOf('python3 build-actions.py') > cmd.indexOf('python3 build-synology-cloud-import.py'));
  assert.ok(cmd.indexOf('python3 build-actions.py') < cmd.indexOf('python3 scripts/check-inline-scripts.py'));
});

test('Synology beschermt acties tegen oude clients en audit kan acties herstellen', () => {
  assert.match(dataApi, /Oudere clients kennen de Acties-store/);
  assert.match(dataApi, /\\$data\\['actions'\\]/);
  assert.match(auditLib, /'actions' => 'Acties'/);
  assert.match(auditLib, /breakdowns','actions/);
  assert.match(auditLog, /breakdowns','actions/);
});

test('Actiegebruikers-API deelt alleen minimale gebruikersinfo met aangemelde gebruikers', () => {
  assert.match(userApi, /mp_auth_require_user/);
  assert.match(userApi, /mp_auth_public_user/);
  assert.match(userApi, /roleLabel/);
  assert.doesNotMatch(userApi, /passwordHash/);
});

test('Acties heeft een expliciet Synology-weergaverecht en blijft zichtbaar voor bestaande ingebouwde rollen', () => {
  assert.match(roleLib, /view\.actions/);
  assert.match(roleLib, /Acties bekijken/);
  assert.match(roleLib, /view\.manuals','view\.actions','view\.parts/);
  assert.match(roleLib, /view\.dashboard','view\.actions','view\.parts/);
  assert.match(builder, /breakdowns','actions','faults/);
});

test('een actie kan veilig verwijderd worden vanuit het detailscherm', () => {
  assert.match(builder, /async function deleteAction\(id\)/);
  assert.match(builder, /await del\('actions',item\.id\)/);
  assert.match(builder, /Actie .* definitief verwijderen/);
  assert.match(builder, /className='btn danger'/);
  assert.match(builder, /remove\.textContent='Verwijderen'/);
  assert.match(builder, /toast\('Actie verwijderd'\)/);
});

test('Acties ondersteunt status In behandeling binnen Nog te doen', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /In behandeling/);
  assert.match(linking, /setActionWorkStatus/);
  assert.match(linking, /status==='in_progress'/);
  assert.match(linking, /Nog te doen/);
});

test('bestaande open of in behandeling zijnde actie kan aan service gekoppeld worden', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /linkExistingActionToService/);
  assert.match(linking, /Bestaande actie koppelen/);
  assert.match(linking, /a\.status!==['"]done['"]/);
  assert.match(linking, /serviceReportIds/);
  assert.match(linking, /Ontkoppelen/);
});

test('serviceverslagstatus volgt gekoppelde actiestatus', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /machineparkServiceReportStatus/);
  assert.match(linking, /In behandeling/);
  assert.match(linking, /return 'Open'/);
  assert.match(linking, /return 'Afgesloten'/);
  assert.match(linking, /service-visit-status/);
});


test('serviceoverzicht opnieuw na actierefresh', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /renderMachineparkServiceVisits/);
  assert.match(linking, /renderAll/);
  assert.match(linking, /servicestatus refresh/);
});


test('nieuw serviceconcept kan bestaande actie koppelen vóór afsluiten', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /Actie koppelen/);
  assert.match(linking, /machineparkOpenServiceDraftActionPicker/);
  assert.match(linking, /linkedActionIds/);
  assert.match(linking, /draftReportId/);
  assert.match(linking, /header\.draftReportId\|\|uid\('sr'\)/);
  assert.match(linking, /machineparkFinalizeServiceDraftActions/);
});

test('serviceconcept bewaart en ruimt actiekoppelingen correct op', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /Koppeling bewaren/);
  assert.match(linking, /Gekoppeld aan serviceconcept/);
  assert.match(linking, /machineparkClearServiceDraftActionLinks/);
  assert.match(linking, /service-draft-action-picker-backdrop/);
});


test('service-visits krijgt cache-busting na actiekoppeling-build', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /sha256\(service\.encode/);
  assert.match(linking, /service-visits\\\.js\\\?v=/);
  assert.match(linking, /service_src_count/);
  assert.match(linking, /INDEX\.write_text\(index/);
});


test('service-actie afrondvinkje rondt gekoppelde actie direct af', () => {
  const completion = readFileSync(new URL('../build-action-service-completion.py', import.meta.url), 'utf8');
  assert.match(completion, /completeLinkedActionFromService/);
  assert.match(completion, /service-action-complete-check/);
  assert.match(completion, /data-service-action-complete/);
  assert.match(completion, /completedDate:todayISO\(\)/);
  assert.match(completion, /Actie afgerond/);
  assert.match(completion, /linked\.has\(String\(action\.id/);
});

test('service-actie afrondvinkje bouwt na de servicekoppeling', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-action-service-completion.py'));
  assert.ok(cmd.indexOf('python3 build-action-service-completion.py') > cmd.indexOf('python3 build-action-service-linking.py'));
});


test('machine-acties staan in de chronologische tijdlijn en niet in een apart vak', () => {
  const timeline = readFileSync(new URL('../build-action-machine-timeline.py', import.meta.url), 'utf8');
  assert.match(timeline, /type:'action'/);
  assert.match(timeline, /event-label action/);
  assert.match(timeline, /data-action-open/);
  assert.match(timeline, /events\.sort/);
  assert.match(timeline, /function deviceActionsHtml\(deviceId\).*in index/);
  assert.match(timeline, /decorateContextModal\('device',deviceId\)/);
});

test('machine-actietijdlijn bouwt na de acties en servicekoppeling', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-action-machine-timeline.py'));
  assert.ok(cmd.indexOf('python3 build-action-machine-timeline.py') > cmd.indexOf('python3 build-actions.py'));
  assert.ok(cmd.indexOf('python3 build-action-machine-timeline.py') > cmd.indexOf('python3 build-action-service-completion.py'));
});
