import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { assertSnapshotWriteAllowed } from '../netlify/functions/_shared/permissions.mjs';

const js = readFileSync(new URL('../service-visits.js', import.meta.url), 'utf8');

test('serviceverslag kan alleen volledig verwijderd worden met de juiste onderhoud- en depannagerechten', () => {
  assert.match(js, /svCanDeleteReport/);
  assert.match(js, /maintenance\.delete/);
  assert.match(js, /breakdowns\.delete/);
  assert.match(js, /Deze rol mist het verwijderrecht voor één of meer gekoppelde werkzaamheden/);
});

test('serviceverslag verwijdert gekoppelde onderhouds- en depannageregistraties atomair', () => {
  assert.match(js, /function deleteServiceReportAtomic/);
  assert.match(js, /serviceReportDeleteRows/);
  assert.match(js, /db\.transaction\(\['maintenance','breakdowns','parts'\],'readwrite'\)/);
  assert.match(js, /impact\.rows\.maintenance\.forEach\(record=>ms\.delete\(record\.id\)\)/);
  assert.match(js, /impact\.rows\.breakdowns\.forEach\(record=>bs\.delete\(record\.id\)\)/);
});

test('gebruikte voorraadonderdelen worden exact terug op voorraad gezet', () => {
  assert.match(js, /totals\[id\]=\(totals\[id\]\|\|0\)\+qty/);
  assert.match(js, /stock:Number\(part\.stock\|\|0\)\+Number\(qty\|\|0\)/);
  assert.match(js, /terug op voorraad gezet/);
});

test('detailvenster toont een expliciete verwijderknop', () => {
  assert.match(js, /service-visit-delete-btn/);
  assert.match(js, /del\.textContent='Verwijderen'/);
  assert.match(js, /deleteServiceReport\(report\.id\)/);
  assert.match(js, /Serviceverslag .* definitief verwijderen/);
});

test('serverrechten laten voorraadherstel toe wanneer gekoppeld onderhoud en depannage worden verwijderd', () => {
  const before = {
    app:'Machinepark', schema:1,
    devices:[{id:'d1',assetCode:'WCL-1',status:'Actief'}],
    parts:[{id:'p1',artNr:'P1',stock:2}],
    maintenance:[{
      id:'m1',deviceId:'d1',type:'Jaarlijks',serviceVisitId:'sv1',serviceReportId:'sr1',
      usedParts:[{partId:'p1',qty:1}],
    }],
    breakdowns:[{
      id:'b1',deviceId:'d1',issue:'Storing',serviceVisitId:'sv1',serviceReportId:'sr1',
      usedParts:[{partId:'p1',qty:2}],
    }],
  };
  const after = {
    ...before,
    parts:[{id:'p1',artNr:'P1',stock:5}],
    maintenance:[],
    breakdowns:[],
  };
  const roleConfig = {
    version:1,
    roles:[{
      id:'serviceverwijderaar',
      label:'Serviceverwijderaar',
      permissions:{'maintenance.delete':true,'breakdowns.delete':true},
    }],
  };
  assert.doesNotThrow(() => assertSnapshotWriteAllowed(before,after,'serviceverwijderaar',roleConfig));
});

test('server blokkeert een gemengd serviceverslag als één verwijderrecht ontbreekt', () => {
  const before = {
    app:'Machinepark', schema:1,
    devices:[{id:'d1',assetCode:'WCL-1',status:'Actief'}],
    parts:[{id:'p1',artNr:'P1',stock:2}],
    maintenance:[{id:'m1',deviceId:'d1',type:'Jaarlijks',serviceVisitId:'sv1',serviceReportId:'sr1',usedParts:[]}],
    breakdowns:[{id:'b1',deviceId:'d1',issue:'Storing',serviceVisitId:'sv1',serviceReportId:'sr1',usedParts:[]}],
  };
  const after = {...before,maintenance:[],breakdowns:[]};
  const roleConfig = {
    version:1,
    roles:[{
      id:'alleenonderhoud',
      label:'Alleen onderhoud',
      permissions:{'maintenance.delete':true},
    }],
  };
  assert.throws(() => assertSnapshotWriteAllowed(before,after,'alleenonderhoud',roleConfig), /depannage verwijderen/i);
});
