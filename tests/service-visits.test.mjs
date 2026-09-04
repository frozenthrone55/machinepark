import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assertSnapshotWriteAllowed } from '../netlify/functions/_shared/permissions.mjs';

const js = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const css = readFileSync(new URL('../service-visits.css', import.meta.url), 'utf8');
const build = readFileSync(new URL('../build-service-visits.py', import.meta.url), 'utf8');
const mail = readFileSync(new URL('../build-mail-pdf-direct.py', import.meta.url), 'utf8');
const manuals = readFileSync(new URL('../manual-library.js', import.meta.url), 'utf8');
const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'));

test('servicebezoek groepeert onderhoud en depannage via één serviceVisitId', () => {
  assert.match(js, /serviceVisitId/);
  assert.match(js, /serviceVisitNumber/);
  assert.match(js, /serviceVisitLocation/);
  assert.match(js, /state\.maintenance/);
  assert.match(js, /state\.breakdowns/);
  assert.match(js, /Werkzaamheden per toestel/);
});

test('onderdelen blijven per toestel en worden alleen voor klant samengevoegd', () => {
  assert.match(js, /perRecordPartsText/);
  assert.match(js, /mergedVisitParts/);
  assert.match(js, /Onderdelen blijven gekoppeld aan dit toestel/);
  assert.match(js, /Onderdelen · samengevoegd voor klant/);
  assert.match(js, /devices:new Set/);
});

test('serviceverslagdetails tonen Bewerken en toevoegacties zitten alleen in bewerkmodus', () => {
  assert.match(js, /edit\.textContent='✏️ Bewerken'/);
  assert.match(js, /openServiceVisit\(report\.id,'',\{edit:true\}\)/);
  assert.match(js, /id="serviceReportAddLocation"/);
  assert.match(js, /id="serviceReportAddDevice"/);
  const detailStart=js.indexOf('function showServiceReportDetails');
  const detailEnd=js.indexOf('function showServiceVisitDetails',detailStart);
  const detail=js.slice(detailStart,detailEnd);
  assert.doesNotMatch(detail, /addDevice\.textContent='\+ Toestel toevoegen'/);
  assert.doesNotMatch(detail, /addLocation\.textContent='\+ Locatie toevoegen'/);
});

test('serviceverslag bewerken behoudt bestaande record ids en corrigeert alleen voorraaddelta', () => {
  assert.match(js, /sourceRecordId/);
  assert.match(js, /sourceUsedParts/);
  assert.match(js, /id:item\.sourceRecordId\|\|item\.id/);
  assert.match(js, /stockUpdates\(selected,\{editMode:Boolean\(header\.editMode\)\}\)/);
  assert.match(js, /totals\[id\]=\(totals\[id\]\|\|0\)-qty/);
  assert.match(js, /serviceReportRevision/);
});



test('meerdere locaties delen één rapport maar behouden een eigen serviceVisitId', () => {
  assert.match(js, /serviceReportId/);
  assert.match(js, /serviceReportNumber/);
  assert.match(js, /serviceReports\(\)/);
  assert.match(js, /draftLocationKey/);
  assert.match(js, /locations,activeLocationKey/);
  assert.match(js, /groups=new Map\(\)/);
  assert.match(js, /existing\?\.id\|\|loc\.visitId\|\|uid\('sv'\)/);
  assert.match(js, /reportId=report\?\.id\|\|header\.appendToReportId\|\|uid\('sr'\)/);
});

test('concept bewaart locaties en werktijd apart per locatie', () => {
  assert.match(js, /locationSessions/);
  assert.match(js, /captureActiveLocationSessions/);
  assert.match(js, /renderActiveLocationSessions/);
  assert.match(js, /serviceReportLocationChips/);
  assert.match(js, /serviceReportAddLocation/);
  assert.match(js, /data-sv-location-remove/);
});

test('pdf groepeert per locatie en toont ook totaalonderdelen over alle locaties', () => {
  assert.match(js, /mergedReportParts/);
  assert.match(js, /reportHtml/);
  assert.match(js, /LOCATIE ·/);
  assert.match(js, /Totaal gebruikte onderdelen · alle locaties/);
  assert.match(css, /service-report-location/);
});

test('volledig servicebezoek heeft concept autosave en boekt voorraad pas bij afsluiten', () => {
  assert.match(js, /AUTOSAVE_DELAY = 1400/);
  assert.match(js, /Concept bewaren/);
  assert.match(js, /draftKind:'serviceVisit'/);
  assert.match(js, /scheduleDraft/);
  assert.match(js, /saveDraftInternal/);
  assert.match(js, /stockUpdates\(selected\)/);
  assert.match(js, /db\.transaction\(\['maintenance','breakdowns','parts'\]/);
  assert.match(js, /machineparkSyncOnlineNow/);
});

test('handleidingen zijn per toestel beschikbaar in onderhoud en depannage binnen servicebezoek', () => {
  assert.match(js, /data-sv-manuals/);
  assert.match(js, /📘 Handleidingen/);
  assert.match(js, /machineparkManualListHtml/);
  assert.match(manuals, /window\.machineparkManualsForDevice/);
  assert.match(manuals, /window\.machineparkManualListHtml/);
});

test('bestaande werkbonnen storingskoppeling en meerdaagse werktijd blijven beschikbaar', () => {
  assert.match(js, /machineparkMakeWorkOrderEditor/);
  assert.match(js, /machineparkCollectWorkOrder/);
  assert.match(js, /machineparkAugmentBreakdownFaultCards/);
  assert.match(js, /machineparkFaultRefFromCard/);
  assert.match(js, /machineparkServiceWorkSessionsEditor/);
  assert.match(js, /machineparkCollectWorkSessions/);
  assert.match(js, /Gekoppelde storing/);
  assert.match(js, /Werkbon/);
});

test('gezamenlijk verslag ondersteunt afdruk en Mail PDF', () => {
  assert.match(js, /service-visit-print-btn/);
  assert.match(js, /service-visit-mail-btn/);
  assert.match(js, /machineparkServiceVisitPdfModel/);
  assert.match(css, /service-visit-print-sheet/);
  assert.match(mail, /service-visit-mail-btn/);
  assert.match(mail, /machineparkServiceVisitPdfModel/);
  assert.match(mail, /context\.kind === 'serviceVisit'/);
});

test('servicebezoek bouwt na Werkzaamheden, wordt syntax-gecontroleerd en cacheveilig versiegebonden', () => {
  const chain = pkg.scripts.build;
  assert.ok(chain.indexOf('build-work-activities.py') < chain.indexOf('build-service-visits.py'));
  assert.ok(chain.includes('node --check service-visits.js'));
  assert.match(build, /service-visits\.js/);
  assert.match(build, /service-visits\.css/);
  assert.match(build, /hashlib\.sha256/);
  assert.match(build, /service_js_url = f'\/service-visits\.js\?v=\{service_hash\}'/);
  assert.match(build, /service_css_url = f'\/service-visits\.css\?v=\{service_hash\}'/);
});

test('servicebezoek volgt bestaande regel dat voorraad negatief mag worden', () => {
  assert.doesNotMatch(js, /if\(Number\(p\.stock\|\|0\)<qty\)throw new Error/);
  assert.match(js, /stock:Number\(p\.stock\|\|0\)-qty/);
});

test('serviceconcepten passen binnen bestaande serverrechten voor onderhoud en depannage', () => {
  const base = {
    app:'Machinepark', schema:1,
    devices:[{id:'d1',assetCode:'WCL-1',status:'Actief'}],
    parts:[{id:'p1',artNr:'P1',stock:5}],
    maintenance:[], breakdowns:[],
  };
  const roleConfig = {
    version:1,
    roles:[{
      id:'techniek', label:'Techniek',
      permissions:{'maintenance.add':true,'breakdowns.add':true},
    }],
  };
  const header = {id:'svdraft1',isDraft:true,draftRole:'header',draftKind:'serviceVisit',draftBatchId:'svdraft1',draftHeaderStore:'breakdowns'};
  const maintenance = {id:'m1',isDraft:true,draftRole:'item',draftKind:'serviceVisit',draftBatchId:'svdraft1',draftServiceKind:'maintenance',deviceId:'d1',usedParts:[{partId:'p1',qty:1}]};
  const breakdown = {id:'b1',isDraft:true,draftRole:'item',draftKind:'serviceVisit',draftBatchId:'svdraft1',draftServiceKind:'breakdowns',deviceId:'d1',issue:'Storing',usedParts:[]};
  const draft = {...base, maintenance:[maintenance], breakdowns:[header,breakdown]};
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(base,draft,'techniek',roleConfig));

  const final = {
    ...base,
    parts:[{...base.parts[0],stock:4}],
    maintenance:[{...maintenance,isDraft:undefined,draftRole:undefined,draftKind:undefined,draftBatchId:undefined,draftServiceKind:undefined,serviceVisitId:'sv1'}],
    breakdowns:[{...breakdown,isDraft:undefined,draftRole:undefined,draftKind:undefined,draftBatchId:undefined,draftServiceKind:undefined,serviceVisitId:'sv1'}],
  };
  delete final.maintenance[0].isDraft; delete final.maintenance[0].draftRole; delete final.maintenance[0].draftKind; delete final.maintenance[0].draftBatchId; delete final.maintenance[0].draftServiceKind;
  delete final.breakdowns[0].isDraft; delete final.breakdowns[0].draftRole; delete final.breakdowns[0].draftKind; delete final.breakdowns[0].draftBatchId; delete final.breakdowns[0].draftServiceKind;
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(draft,final,'techniek',roleConfig));
});
