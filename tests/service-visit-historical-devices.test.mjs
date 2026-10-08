import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync('service-visits.js','utf8');
const helper=source.slice(source.indexOf('  function findGroup('),source.indexOf('  function renderDevices('));
function setup(devices,groups,draft){
  const context={state:{devices},activeVisitDraft:draft,locationGroups:()=>groups,
    svKey:value=>String(value||'').toLowerCase().trim(),
    visitForLocation:(report,key)=>(report?.visits||[]).find(v=>v.locationKey===key),
    locationItems:(items,key,fallback)=>(items||[]).filter(i=>(i.draftLocationKey||fallback)===key)};
  vm.createContext(context);vm.runInContext(helper+'\nthis.find=findGroup;',context);return context;
}
test('editing keeps original moved and inactive devices alongside current devices without duplicates',()=>{
  const devices=[{id:'moved',location:'New site',status:'Buiten dienst'},{id:'stayed',location:'Old site'},{id:'new',location:'Old site'}];
  const groups=[{key:'old',label:'Old site',devices:[devices[1],devices[2]]}];
  const draft={locations:[{key:'old',label:'Old site'}],items:[{deviceId:'moved',draftLocationKey:'old'}],report:{visits:[{locationKey:'old',location:'Old site',records:[{item:{deviceId:'moved'}},{item:{deviceId:'stayed'}}]}]}};
  const c=setup(devices,groups,draft),result=c.find('old','Old site');
  assert.deepEqual(Array.from(result.devices,d=>d.id),['stayed','new','moved']);
  assert.equal(result.label,'Old site');assert.equal(groups[0].devices.length,2);assert.equal(devices[0].location,'New site');
});
test('a saved draft reopens an old location even with no current location group',()=>{
  const c=setup([{id:'moved',location:'New site'}],[],{locations:[{key:'old',label:'Old site'}],items:[{deviceId:'moved',draftLocationKey:'old'},{deviceId:'elsewhere',draftLocationKey:'other'}]});
  assert.deepEqual(Array.from(c.find('old').devices,d=>d.id),['moved']);
  assert.equal(c.find('missing'),null);
});
test('a new service location retains its existing device selection',()=>{
  const group={key:'new',label:'New site',devices:[{id:'d'}]};
  const c=setup(group.devices,[group],{locations:[],items:[]});assert.equal(c.find('new'),group);
});
