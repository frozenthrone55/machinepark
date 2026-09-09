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


test('service verwijderen ruimt actiekoppeling atomair op', () => {
  const cleanup = readFileSync(new URL('../build-action-service-delete-cleanup.py', import.meta.url), 'utf8');
  assert.match(cleanup, /serviceReportLinkedActions\(reportId\)/);
  assert.match(cleanup, /maintenance','breakdowns','parts','actions/);
  assert.match(cleanup, /serviceReportIds/);
  assert.match(cleanup, /serviceLinks/);
  assert.match(cleanup, /sourceKind:'',sourceId:'',sourceLabel:''/);
  assert.match(cleanup, /Serviceverslag verwijderd/);
  assert.match(cleanup, /actionUnlinked/);
});

test('service-delete cleanup draait na service- en tijdlijnbouw', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-action-service-delete-cleanup.py'));
  assert.ok(cmd.indexOf('python3 build-action-service-delete-cleanup.py') > cmd.indexOf('python3 build-action-service-linking.py'));
  assert.ok(cmd.indexOf('python3 build-action-service-delete-cleanup.py') > cmd.indexOf('python3 build-action-machine-timeline.py'));
});


test('zichtbare Acties-module heet ToDo', () => {
  const labels = readFileSync(new URL('../build-todo-labels.py', import.meta.url), 'utf8');
  assert.match(labels, /<span class="label">ToDo<\/span>/);
  assert.match(labels, /Nieuwe ToDo snel toevoegen/);
  assert.match(labels, /Open ToDo’s/);
  assert.match(labels, /Gekoppelde ToDo’s/);
  assert.match(labels, /Bestaande ToDo koppelen/);
  assert.match(labels, /ToDo afronden/);
  assert.match(labels, /state\.actions/);
});

test('ToDo-labels draaien als laatste actie-naamlaag', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-todo-labels.py'));
  assert.ok(cmd.indexOf('python3 build-todo-labels.py') > cmd.indexOf('python3 build-action-service-delete-cleanup.py'));
  assert.ok(cmd.indexOf('python3 build-todo-labels.py') < cmd.indexOf('node --check service-visits.js'));
});


test('dashboard KPI kaarten openen modules en oude blokken verdwijnen', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /data-dashboard-kpi="devices"/);
  assert.match(dashboard, /data-dashboard-kpi="maintenance"/);
  assert.match(dashboard, /data-dashboard-kpi="breakdowns"/);
  assert.match(dashboard, /data-dashboard-kpi="parts"/);
  assert.match(dashboard, /kpiActionsCard/);
  assert.match(dashboard, /partStockFilter/);
  assert.match(dashboard, /stock\.value="low"/);
  assert.match(dashboard, /goDashboardKpi/);
  assert.match(dashboard, /dashboardAlerts.*hidden/);
});

test('dashboard KPI navigatie bouwt na ToDo-labels', () => {
  const cmd = pkg.scripts.build;
  assert.ok(cmd.includes('python3 build-dashboard-kpi-navigation.py'));
  assert.ok(cmd.indexOf('python3 build-dashboard-kpi-navigation.py') > cmd.indexOf('python3 build-todo-labels.py'));
  assert.ok(cmd.indexOf('python3 build-dashboard-kpi-navigation.py') < cmd.indexOf('node --check service-visits.js'));
});


test('dashboard onderhoud en depannages gebruiken Werkzaamheden in plaats van lege legacy views', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /route="work"/);
  assert.match(dashboard, /workKindFilter/);
  assert.match(dashboard, /target==="maintenance" \? "maintenance" : "breakdowns"/);
  assert.match(dashboard, /machineparkInlineNavigate/);
  assert.match(dashboard, /machineparkEarlyNavigate/);
  assert.match(dashboard, /machineparkRenderCombinedWork/);
  assert.match(dashboard, /data-dashboard-kpi="maintenance">Alles bekijken/);
});


test('dashboard KPI drilldown toont exact dezelfde selectie als de teller', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /value="service">In servicebeheer/);
  assert.match(dashboard, /maintenance-attention/);
  assert.match(dashboard, /open-attention/);
  assert.match(dashboard, /machineparkDashboardRenderMaintenanceAttention/);
  assert.match(dashboard, /daysUntil\(device\.nextHalf\)<=30/);
  assert.match(dashboard, /bs==='open-attention'/);
  assert.match(dashboard, /serviceKind!=='other'/);
  assert.match(dashboard, /machineparkDashboardTodoOpenOnly/);
  assert.match(dashboard, /actionScope='all'/);
});


test('open service heeft eigen dashboardvenster en staat niet meer in Werkzaamheden', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /view-service-overview/);
  assert.match(dashboard, /kpiOpenServiceCard/);
  assert.match(dashboard, /serviceOverviewStatusFilter/);
  assert.match(dashboard, /Open service/);
  assert.match(dashboard, /Alle serviceverslagen/);
  assert.match(dashboard, /Afgesloten/);
  assert.match(dashboard, /panel\.parentNode!==view/);
  assert.match(dashboard, /view\.appendChild\(panel\)/);
  assert.match(dashboard, /machineparkOpenServiceOverview/);
});

test('open service KPI telt open verslagen en serviceconcepten', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /status==="Open"\|\|status==="In behandeling"/);
  assert.match(dashboard, /data-sv-draft-open/);
  assert.match(dashboard, /kpiOpenService/);
});


test('dashboard KPI volgorde is twee rijen van drie', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /grid-template-columns:repeat\(3,minmax\(0,1fr\)\)/);
  assert.match(dashboard, /\[data-dashboard-kpi="devices"\]\{order:1\}/);
  assert.match(dashboard, /#kpiActionsCard\{order:2\}/);
  assert.match(dashboard, /\[data-dashboard-kpi="parts"\]\{order:3\}/);
  assert.match(dashboard, /#kpiOpenServiceCard\{order:4\}/);
  assert.match(dashboard, /\[data-dashboard-kpi="breakdowns"\]\{order:5\}/);
  assert.match(dashboard, /\[data-dashboard-kpi="maintenance"\]\{order:6\}/);
  assert.match(dashboard, /max-width:1050px/);
  assert.match(dashboard, /max-width:680px/);
});


test('open service blijft actief na synchronisatie en render', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /restoreServiceOverviewActive/);
  assert.match(dashboard, /state\.view!=="service-overview"/);
  assert.match(dashboard, /navigate\("service-overview"\)/);
  assert.match(dashboard, /restoreServiceOverviewActive\(\);\n    serviceOverviewApplyFilter/);
  assert.match(dashboard, /updateOpenServiceKpi\(\);restoreServiceOverviewActive\(\)/);
  assert.match(dashboard, /service-overview.*Open service/);
});


test('dashboardfilters gelden alleen bij dashboardnavigatie', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkDashboardNavigationTarget/);
  assert.match(dashboard, /machineparkResetDashboardDrilldownFilters/);
  assert.match(dashboard, /const fromDashboardKpi = dashboardTarget === nextView/);
  assert.match(dashboard, /machineparkResetDashboardDrilldownFilters\(nextView\)/);
});

test('gewone tabbladen herstellen volledige overzichten', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /if\(device\)device\.value=""/);
  assert.match(dashboard, /if\(stock\)stock\.value=""/);
  assert.match(dashboard, /if\(kind\)kind\.value=""/);
  assert.match(dashboard, /if\(breakdownStatus\)breakdownStatus\.value=""/);
  assert.match(dashboard, /machineparkDashboardTodoOpenOnly=false/);
  assert.match(dashboard, /doneSection\.style\.display=""/);
  assert.match(dashboard, /serviceFilter\.value="all"/);
});

test('dashboard KPI markeert navigatiecontext vóór filterroute', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkDashboardNavigationTarget='actions'/);
  assert.match(dashboard, /machineparkDashboardNavigationTarget="service-overview"/);
  assert.match(dashboard, /machineparkDashboardNavigationTarget=route/);
});


test('open service gebruikt bestaande onderhoud of depannagerechten', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /view === 'service-overview'/);
  assert.match(dashboard, /hasPermission\('view\.maintenance'\)/);
  assert.match(dashboard, /return 'view\.breakdowns'/);
  assert.doesNotMatch(dashboard, /return 'view\.service-overview'/);
});

test('open service metadata is bekend bij vaste navigatieruntime', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /'service-overview': \['Open service'/);
});


test('werkzaamheden tabblad toont service maar dashboard drilldown niet', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /currentView==="work"&&workView/);
  assert.match(dashboard, /workView\.appendChild\(panel\)/);
  assert.match(dashboard, /panel\.style\.display=dashboardWork\?"none":""/);
  assert.match(dashboard, /overviewFilter\.value="all"/);
  assert.match(dashboard, /machineparkDashboardWorkDrilldown/);
});

test('dashboard onderhoud en depannage markeren service als verborgen context', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkDashboardWorkDrilldown=target==="maintenance"\|\|target==="breakdowns"/);
  assert.match(dashboard, /machineparkSyncServiceOverviewPlacement/);
});

test('normaal werkzaamheden tabblad wist dashboardcontext en herplaatst service', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkDashboardWorkDrilldown=false/);
  assert.match(dashboard, /setTimeout\(function\(\)\{if\(typeof window\.machineparkSyncServiceOverviewPlacement/);
});


test('dashboard zoeken toont ToDo resultaten', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /const actionMatches=canSearchActions/);
  assert.match(dashboard, /global-search-head">ToDo/);
  assert.match(dashboard, /data-global-action/);
  assert.match(dashboard, /a\.title,a\.notes,a\.location,a\.assigneeName/);
  assert.match(dashboard, /a\.completedByName,a\.completionNote,a\.sourceLabel/);
  assert.match(dashboard, /linkedDeviceSearchText\(a\.deviceId/);
});

test('dashboard ToDo zoekresultaat opent rechtstreeks details', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkOpenActionDetails=openActionDetails/);
  assert.match(dashboard, /closest\("\[data-global-action\]"\)/);
  assert.match(dashboard, /machineparkOpenActionDetails\(actionResult\.dataset\.globalAction\)/);
  assert.match(dashboard, /closeGlobalSearch/);
});

test('dashboard ToDo zoeken respecteert view actions recht', () => {
  const dashboard = readFileSync(new URL('../build-dashboard-kpi-navigation.py', import.meta.url), 'utf8');
  assert.match(dashboard, /machineparkHasPermission\('view\.actions'\)/);
});


test('verwijderd serviceconcept laat geen ToDo spookhistoriek achter', () => {
  const linking = readFileSync(new URL('../build-action-service-linking.py', import.meta.url), 'utf8');
  assert.match(linking, /serviceReportId:reportId/);
  assert.match(linking, /serviceLinkKind:finalized\?'report':'draft'/);
  assert.match(linking, /machineparkClearServiceDraftActionLinks=async function\(context\)/);
  assert.match(linking, /String\(entry&&entry\.serviceReportId\|\|''\)===reportId/);
  assert.match(linking, /label\.includes\('serviceconcept'\)/);
  assert.match(linking, /remainingIds\.size===0/);
  assert.match(linking, /header\.draftReportId,date:header\.date,locations:/);
});

test('oude verweesde serviceconceptregels worden niet meer getoond in ToDo historiek', () => {
  const actions = readFileSync(new URL('../build-actions.py', import.meta.url), 'utf8');
  assert.match(actions, /const activeServiceIds=new Set/);
  assert.match(actions, /label\.includes\('serviceconcept'\)/);
  assert.match(actions, /entry&&entry\.serviceReportId/);
  assert.match(actions, /return activeServiceIds\.size>0/);
});


test('serviceconcept historiek vereist bestaand concept en niet alleen een oude service-id', () => {
  const actions = readFileSync(new URL('../build-actions.py', import.meta.url), 'utf8');
  assert.match(actions, /existingDraftReportIds=new Set/);
  assert.match(actions, /record\.isDraft===true/);
  assert.match(actions, /record\.draftKind==='serviceVisit'/);
  assert.match(actions, /record\.draftRole==='header'/);
  assert.match(actions, /record\.draftReportId/);
  assert.match(actions, /activeDraftServiceIds=new Set/);
  assert.match(actions, /existingDraftReportIds\.has\(String\(entry\.serviceReportId\)\)/);
  assert.match(actions, /return activeDraftServiceIds\.size>0/);
});


test('machinelogboek toont gebruikte onderdelen onder elkaar', () => {
  const builder = readFileSync(new URL('../build-device-timeline-parts-layout.py', import.meta.url), 'utf8');
  assert.match(builder, /deviceTimelineUsedPartsHtml/);
  assert.match(builder, /device-timeline-used-parts-list/);
  assert.match(builder, /device-timeline-used-part/);
  assert.match(builder, /flex-direction:column/);
  assert.match(builder, /m\.usedParts\?\.length\?deviceTimelineUsedPartsHtml\(m\.usedParts\)/);
  assert.match(builder, /b\.usedParts\?\.length\?deviceTimelineUsedPartsHtml\(b\.usedParts\)/);
});


test('machinelogboek onderdeelregels gebruiken kleiner lettertype', () => {
  const builder = readFileSync(new URL('../build-device-timeline-parts-layout.py', import.meta.url), 'utf8');
  assert.match(builder, /device-timeline-used-part\{display:block;font-size:14px;line-height:1\.35/);
  assert.match(builder, /device-timeline-used-parts>strong\{display:block;margin-bottom:4px\}/);
});


test('afdruk machinelogboek zet werkbon label en waarde onder elkaar', () => {
  const builder = readFileSync(new URL('../build-device-timeline-parts-layout.py', import.meta.url), 'utf8');
  assert.match(builder, /\.timeline-workorder-grid\{display:grid;grid-template-columns:1fr;gap:1\.5mm\}/);
  assert.match(builder, /\.timeline-workorder-field\{display:block\}/);
  assert.match(builder, /\.timeline-workorder-field span\{display:block;font-size:8pt/);
  assert.match(builder, /\.timeline-workorder-field strong\{display:block;font-size:9pt/);
});
