import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assertSnapshotWriteAllowed } from '../netlify/functions/_shared/permissions.mjs';

const js = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');
const other = readFileSync(new URL('../build-other-works.py', import.meta.url), 'utf8');

test('nieuw serviceverslag biedt Andere werken als derde toestelkeuze', () => {
  assert.match(js, /data-kind="otherworks"/);
  assert.match(js, /data-panel-kind="otherworks"/);
  assert.match(js, /> Andere werken/);
  assert.match(js, /Kies per toestel Onderhoud, Depannage en\/of Andere werken/);
});

test('Andere werken gebruikt dezelfde leerbare werksoorten als losse Andere werken', () => {
  assert.match(js, /function svOtherWorkTypeNames/);
  assert.match(js, /\['Plaatsing'\]/);
  assert.match(js, /Nieuwe naam toevoegen/);
  assert.match(js, /workTypeName:collectSvOtherWorkType\(panel\)/);
  assert.match(js, /serviceKind:'other'/);
  assert.match(other, /serviceKind==='other'/);
  assert.match(other, /workTypeName/);
});

test('Andere werken blijft per toestel volledig in serviceconcept bewaard', () => {
  assert.match(js, /for\(const kind of \['maintenance','breakdowns','otherworks'\]\)/);
  assert.match(js, /draftServiceKind:kind/);
  assert.match(js, /collectUsed\(panel\)/);
  assert.match(js, /collectOneOff\(panel\)/);
  assert.match(js, /collectPhotos\(panel,kind/);
  assert.match(js, /machineparkCollectWorkOrder/);
});

test('afsluiten schrijft Andere werken naar bestaande breakdown-opslag met serviceKind other', () => {
  assert.match(js, /kind==='otherworks'/);
  assert.match(js, /serviceKind:'other'/);
  assert.match(js, /finals\.forEach\(i=>\(i\.type!==undefined\?ms:bs\)\.put\(i\)\)/);
  assert.match(other, /isOtherWork=item=>Boolean\(item&&item\.serviceKind==='other'/);
});

test('serviceverslag telt en toont Andere werken apart van depannages', () => {
  assert.match(js, /otherWorkCount:records\.filter\(row => row\.kind === 'otherworks'\)\.length/);
  assert.match(js, /breakdownCount:reportRows\.filter\(item=>item\.type === undefined && !svIsOtherWork\(item\)\)\.length/);
  assert.match(js, /otherWorkCount:reportRows\.filter\(item=>svIsOtherWork\(item\)\)\.length/);
  assert.match(js, /r\.otherWorkCount/);
  assert.match(js, /visit\.otherWorkCount\|\|0/);
  assert.match(js, /svKindLabel\(row\.kind,row\.item\)/);
});

test('serviceverslag verwijderen verwijdert Andere werken mee en reset dezelfde voorraad', () => {
  assert.match(js, /otherWorks:rows\.breakdowns\.filter\(item=>svIsOtherWork\(item\)\)\.length/);
  assert.match(js, /impact\.otherWorks/);
  assert.match(js, /stock:Number\(part\.stock\|\|0\)\+Number\(qty\|\|0\)/);
  assert.match(js, /impact\.rows\.breakdowns\.forEach\(record=>bs\.delete\(record\.id\)\)/);
});

test('server behandelt Andere werken als breakdown-recht zonder nieuwe permissiecategorie', () => {
  const before={
    app:'Machinepark',schema:1,
    devices:[{id:'d1',assetCode:'WCL-1',status:'Actief'}],
    parts:[{id:'p1',artNr:'P1',stock:5}],
    maintenance:[],breakdowns:[],
  };
  const after={
    ...before,
    parts:[{...before.parts[0],stock:4}],
    breakdowns:[{
      id:'o1',deviceId:'d1',serviceKind:'other',workTypeName:'Plaatsing',
      issue:'Nieuwe machine geplaatst',status:'Opgelost',priority:'Normaal',
      serviceVisitId:'sv1',serviceReportId:'sr1',usedParts:[{partId:'p1',qty:1}],
    }],
  };
  const roleConfig={version:1,roles:[{id:'techniek',label:'Techniek',permissions:{'breakdowns.add':true}}]};
  assert.doesNotThrow(()=>assertSnapshotWriteAllowed(before,after,'techniek',roleConfig));
});
