import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
const at='2026-10-06T16:00:00.000Z';
const old={id:'dev_1',assetCode:'WCL0001',location:'Hal 1',brand:'Oud',status:'Actief',notes:'Bewaren',photos:['photo-reference'],installDate:'2020-01-01',installDatePrecision:'day',installDateSource:'1/1/2020',nextHalf:'2027-01-01',locationHistory:[{id:'loc1',location:'Hal 1',effectiveFrom:'2020-01-01T00:00'}]};
const headers=['WCL NR.','ZAAKNAAM','TOESTELLEN','Contract start'];
function run(rows,devices=[old],redRows=[]){return JSON.parse(execFileSync('node',['synology/device-sync-worker.cjs'],{input:JSON.stringify({matrix:[headers,...rows],redRows,devices,fileName:'inventaris.xlsx',syncMoment:'2026-10-06T18:00',loggedAt:at}),encoding:'utf8'}));}
test('automatic sync applies the manual rules, preserves unrelated fields and logs before/after',()=>{
 const r=run([['WCL0001','Hal 2','Nieuw','10/2026'],['WCL0002','Hal 3','Toestel B','']], [old], [1]);
 assert.equal(r.added,1);assert.equal(r.updated,1);
 const d=r.devices.find(d=>d.id==='dev_1');
 assert.equal(d.location,'Hal 2');assert.equal(d.status,'Buiten dienst');assert.equal(d.brand,'Nieuw');
 assert.equal(d.installDate,'2026-10-01');assert.equal(d.installDatePrecision,'month');
 assert.equal(d.notes,old.notes);assert.deepEqual(d.photos,old.photos);assert.equal(d.nextHalf,old.nextHalf);
 assert.equal(d.locationHistory.at(-1).effectiveFrom,'2026-10-06T18:00');
 assert.ok(r.changes.some(c=>c.code==='WCL0001'&&c.field==='location'&&c.oldValue==='Hal 1'&&c.newValue==='Hal 2'));
});
test('blank cells never erase values, missing devices are never deleted, inactive status is not reactivated',()=>{
 const r=run([['WCL0001','','','']], [{...old,status:'Buiten dienst'},{id:'other',assetCode:'WCL9999'}]);
 assert.deepEqual(r.devices,[]);assert.equal(r.unchanged,1);assert.equal(r.changes.length,0);
});
test('duplicate codes fail before any write',()=>{
 assert.throws(()=>run([['WCL0001','A','',''],['wcl0001','B','','']]),/Dubbele WCL-nummers/);
});
test('invalid headers and empty inventories fail instead of advancing a version',()=>{
 assert.throws(()=>run([]),/Geen geldige toestellen/);
 assert.throws(()=>JSON.parse(execFileSync('node',['synology/device-sync-worker.cjs'],{input:JSON.stringify({matrix:[['Code','Locatie']],devices:[],redRows:[]}),encoding:'utf8'})),/Kolommen/);
});
test('runtime package includes both UI and shared worker and offline cache includes UI',()=>{
 const pkg=readFileSync('scripts/package-synology-runtime.py','utf8');
 assert.match(pkg,/"sharepoint-device-sync.js"/);assert.match(pkg,/"synology\/device-sync-worker.cjs"/);
 assert.match(readFileSync('sw.js','utf8'),/\.\/sharepoint-device-sync.js/);
 assert.match(readFileSync('index.html','utf8'),/<script src="\.\/sharepoint-device-sync.js\?v=[a-f0-9]{16}"><\/script>/);
});
test('PHP parser, atomic persistence and errors are verified in isolated storage',()=>{
 const output=execFileSync('php',['tests/sharepoint-device-sync.php'],{encoding:'utf8'});
 assert.match(output,/sharepoint sync PHP checks passed/);
});
