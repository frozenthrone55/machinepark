import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const source=readFileSync('composed-location-history.js','utf8');
function setup(state){
 const context={state,composedKey:v=>String(v||'').toLowerCase().trim(),composedClone:v=>JSON.parse(JSON.stringify(v)),composedHistoryMoment:r=>r.date||r.createdAt||'',usedPartIds:rows=>new Set(rows.flatMap(r=>(r.usedParts||[]).map(p=>p.partId)))};
 vm.createContext(context);vm.runInContext(source.slice(0,source.indexOf('  const composedAllLocationHistoryRows'))+'\nthis.snapshot=composedLocationSnapshot;this.choices=composedLocationChoices;',context);return context;
}
test('location includes departed devices and both movement directions but excludes later work elsewhere',()=>{
 const d={id:'d',assetCode:'WCL1',location:'B',locationHistory:[{location:'A',effectiveFrom:'2024-01-01'},{location:'B',effectiveFrom:'2025-01-01'}]};
 const c=setup({devices:[d],maintenance:[{id:'a',deviceId:'d',date:'2024-06-01',usedParts:[{partId:'p'}]},{id:'b',deviceId:'d',date:'2025-06-01'}],breakdowns:[{id:'other',deviceId:'d',date:'2024-07-01',serviceKind:'other'}],parts:[{id:'p'},{id:'unused'}]});
 const s=c.snapshot(['A']);assert.equal(s.devices.length,1);assert.deepEqual(Array.from(s.maintenance,r=>r.id),['a']);assert.equal(s.breakdowns[0].id,'other');assert.equal(s.parts.length,1);assert.deepEqual(Array.from(s.locationMovements,r=>r.kind),['Registratie toestel','Vertrek toestel']);assert.equal(c.snapshot(['B']).locationMovements[0].kind,'Aankomst toestel');
 assert.equal(d.locationHistory.length,2);
});
test('explicit historic record location wins and locations without current devices remain selectable',()=>{
 const c=setup({devices:[],maintenance:[{id:'old',deviceId:'deleted',date:'2020-01-01',location:'Former site'}],breakdowns:[{id:'draft',location:'Draft site',isDraft:true}],parts:[]});
 assert.deepEqual(Array.from(c.choices()),['Former site']);const s=c.snapshot(['Former site']);assert.equal(s.maintenance.length,1);assert.equal(s.devices[0].id,'deleted');
});
test('multiple locations merge records once and include arrivals and departures',()=>{
 const c=setup({devices:[{id:'d',location:'B',locationHistory:[{location:'A',effectiveFrom:'2024-01-01'},{location:'B',effectiveFrom:'2025-01-01'}]}],maintenance:[{id:'r',deviceId:'d',date:'2024-05-01'}],breakdowns:[],parts:[]});const s=c.snapshot(['A','B']);assert.equal(s.maintenance.length,1);assert.equal(s.devices.length,1);assert.equal(s.locationMovements.length,3);
});
