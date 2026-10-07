  let selectedComposedLocations=new Set();
  function composedLocationEvents(device){
    const rows=Array.isArray(device?.locationHistory)?device.locationHistory.filter(e=>e?.location):[];
    return rows.length?[...rows].sort((a,b)=>String(a.effectiveFrom||'').localeCompare(String(b.effectiveFrom||''))):device?.location?[{location:device.location,effectiveFrom:device.installDate||device.createdAt||''}]:[];
  }
  function composedRecordHistoricalLocation(record,device){
    if(record?.serviceVisitLocation||record?.location)return String(record.serviceVisitLocation||record.location).trim();
    const moment=composedHistoryMoment(record),events=composedLocationEvents(device);
    let location='';
    for(const event of events){if(!event.effectiveFrom||String(event.effectiveFrom)<=moment)location=event.location;else break;}
    return String(location||(!moment?device?.location:'')||'').trim();
  }
  function composedLocationChoices(){
    const locations=new Map(),add=value=>{const name=String(value||'').trim();if(name)locations.set(composedKey(name),name);};
    (state.devices||[]).forEach(d=>{add(d.location);composedLocationEvents(d).forEach(e=>add(e.location));});
    [...(state.maintenance||[]),...(state.breakdowns||[])].forEach(r=>{if(r?.isDraft!==true)add(composedRecordHistoricalLocation(r,(state.devices||[]).find(d=>d.id===r.deviceId)));});
    return [...locations.values()].sort((a,b)=>a.localeCompare(b,'nl',{numeric:true,sensitivity:'base'}));
  }
  function composedLocationSnapshot(locations){
    const keys=new Set(locations.map(composedKey)),original=new Map((state.devices||[]).map(d=>[d.id,d]));
    const matches=r=>r?.isDraft!==true&&keys.has(composedKey(composedRecordHistoricalLocation(r,original.get(r.deviceId))));
    const copyRecord=r=>({...composedClone(r),location:composedRecordHistoricalLocation(r,original.get(r.deviceId))});
    const maintenance=(state.maintenance||[]).filter(matches).map(copyRecord),breakdowns=(state.breakdowns||[]).filter(matches).map(copyRecord);
    const ids=new Set([...maintenance,...breakdowns].map(r=>r.deviceId).filter(Boolean)),locationMovements=[];
    for(const device of original.values()){
      const events=composedLocationEvents(device);
      events.forEach((event,i)=>{
        const previous=events[i-1],from=String(previous?.location||''),to=String(event.location||'');
        if(previous&&composedKey(from)===composedKey(to))return;
        if(keys.has(composedKey(to))){ids.add(device.id);locationMovements.push({deviceId:device.id,location:to,moment:event.effectiveFrom||'',kind:previous?'Aankomst toestel':'Registratie toestel',details:previous?`Van ${from} naar ${to}`:`Eerste geregistreerde locatie: ${to}`});}
        if(previous&&keys.has(composedKey(from))){ids.add(device.id);locationMovements.push({deviceId:device.id,location:from,moment:event.effectiveFrom||'',kind:'Vertrek toestel',details:`Van ${from} naar ${to}`});}
      });
    }
    const devices=[...ids].map(id=>composedClone(original.get(id)||{id,assetCode:'Onbekend toestel',locationHistory:[]}));
    const partIds=usedPartIds([...maintenance,...breakdowns]),parts=(state.parts||[]).filter(p=>partIds.has(p.id)).map(composedClone);
    return {devices,maintenance,breakdowns,parts,todos:[],selectedLocations:[...locations],locationMovements,capturedAt:new Date().toISOString(),scope:'location-history'};
  }
  const composedAllLocationHistoryRows=composedHistoryRows;
  composedHistoryRows=function(snapshot){
    if(snapshot?.scope!=='location-history')return composedAllLocationHistoryRows(snapshot);
    const keys=new Set((snapshot.selectedLocations||[]).map(composedKey));
    const filtered={...snapshot,devices:(snapshot.devices||[]).map(d=>({...d,locationHistory:[]}))};
    const groups=composedAllLocationHistoryRows(filtered).filter(g=>keys.has(composedKey(g.location)));
    for(const movement of snapshot.locationMovements||[]){
      let group=groups.find(g=>composedKey(g.location)===composedKey(movement.location));
      if(!group){group={location:movement.location,events:[]};groups.push(group);}
      const device=(snapshot.devices||[]).find(d=>d.id===movement.deviceId);
      group.events.push({...movement,rows:[],devices:new Set([composedHistoryDeviceLabel(device)]),technicians:new Set()});
    }
    groups.forEach(g=>g.events.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||''))));
    return groups.sort((a,b)=>a.location.localeCompare(b.location,'nl'));
  };
  function renderComposedLocations(){
    const list=document.getElementById('composedLocationList');if(!list)return;
    const q=composedKey(document.getElementById('composedLocationSearch')?.value||'');
    list.innerHTML=composedLocationChoices().filter(name=>!q||composedKey(name).includes(q)).map(name=>`<label style="display:flex;gap:8px;padding:6px"><input type="checkbox" data-composed-location="${composedEsc(name)}" ${selectedComposedLocations.has(name)?'checked':''}>${composedEsc(name)}</label>`).join('')||'<p>Geen locaties gevonden.</p>';
  }
  const composedEnsureWithLocations=ensureComposedUi;
  ensureComposedUi=function(){
    composedEnsureWithLocations();
    const body=document.querySelector('#composedDocumentsWindow .composed-section-body');if(!body||document.getElementById('composedLocationList'))return;
    const panel=document.createElement('div');panel.className='composed-source-panel';
    panel.innerHTML='<h4>Volledige geschiedenis per locatie</h4><p>Vink één of meer locaties aan voor alle geregistreerde toestelbewegingen en werkzaamheden, ook van verhuisde toestellen. Bij een locatiekeuze wordt het overzicht op deze locaties gebaseerd.</p><input id="composedLocationSearch" type="search" placeholder="Zoek een locatie…"><div id="composedLocationList" style="max-height:220px;overflow:auto;margin:8px 0"></div><button type="button" class="btn small" id="composedClearLocations">Locatiekeuze wissen</button>';
    body.prepend(panel);
    document.getElementById('composedLocationSearch').oninput=renderComposedLocations;
    document.getElementById('composedLocationList').onchange=e=>{const cb=e.target.closest('[data-composed-location]');if(!cb)return;if(cb.checked)selectedComposedLocations.add(cb.dataset.composedLocation);else selectedComposedLocations.delete(cb.dataset.composedLocation);};
    document.getElementById('composedClearLocations').onclick=()=>{selectedComposedLocations.clear();renderComposedLocations();};
    renderComposedLocations();
    document.getElementById('composedSaveDocument').onclick=()=>saveComposedDocument();
  };
  const composedOpenWithLocations=openComposedWindow;
  openComposedWindow=function(){selectedComposedLocations.clear();composedOpenWithLocations();const search=document.getElementById('composedLocationSearch');if(search)search.value='';renderComposedLocations();};
  const composedSaveWithoutLocations=saveComposedDocument;
  saveComposedDocument=async function(){
    if(!selectedComposedLocations.size)return composedSaveWithoutLocations();
    const snapshot=composedLocationSnapshot([...selectedComposedLocations]);
    const name=String(document.getElementById('composedDocumentName')?.value||'').trim()||`${snapshot.selectedLocations.join(' · ')} · volledige locatiehistoriek`;
    const now=new Date().toISOString(),entry={id:`cmp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2,8)}`,name,createdAt:now,updatedAt:now,createdBy:composedCurrentUser(),deviceIds:snapshot.devices.map(d=>d.id),selectedLocations:snapshot.selectedLocations,snapshot};
    await persistComposedList([entry,...composedList()]);selectedComposedLocations.clear();renderComposedLocations();composedNotify('Locatiehistoriek opgeslagen');
  };
