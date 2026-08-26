from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')

start=s.find('function partMachineChoices(){')
if start < 0:
    start=s.find('function partForm(p={}){')
end=s.find('\nfunction deviceForm(d={}){', start)
if start < 0 or end < 0:
    raise SystemExit('Onderdeelformulier niet gevonden')

new_block=r'''function partMachineChoices(){const values=new Set();state.parts.forEach(p=>{const label=String(p.deviceBrand||'').trim();if(label)values.add(label)});return [...values].sort((a,b)=>a.localeCompare(b,'nl',{sensitivity:'base'}))}
function partForm(p={}){const current=String(p.deviceBrand||'').trim(),choices=partMachineChoices(),known=current&&choices.includes(current),selected=current?(known?current:'__new__'):'';const options=choices.map(x=>`<option value="${esc(x)}" ${selected===x?'selected':''}>${esc(x)}</option>`).join('');return `<div class="form-grid"><div class="field"><label>Art nr *</label><input name="artNr" required value="${esc(p.artNr||'')}"></div><div class="field"><label>Code leverancier</label><input name="supplierCode" value="${esc(p.supplierCode||'')}"></div><div class="field full"><label>Omschrijving *</label><input name="description" required value="${esc(p.description||'')}"></div><div class="field"><label>Merk / machine voor onderdeel</label><select name="deviceBrandChoice" id="partMachineChoice"><option value="">Geen merk / machine gekozen</option>${options}<option value="__new__" ${selected==='__new__'?'selected':''}>+ Nieuw merk / machine toevoegen…</option></select><div class="muted" style="font-size:11px;margin-top:4px">Deze lijst hoort alleen bij Onderdelen en staat los van de merken bij Toestellen.</div></div><div class="field" id="partNewMachineField" style="${selected==='__new__'?'':'display:none'}"><label>Nieuw merk / machine</label><input name="deviceBrandNew" id="partNewMachine" placeholder="bv. Schaerer Coffee Soul" value="${selected==='__new__'?esc(current):''}"><div class="muted" style="font-size:11px;margin-top:4px">Na opslaan verschijnt deze keuze voortaan alleen in de onderdelenlijst.</div></div><div class="field"><label>Prijs (€)</label><input name="price" type="number" step="0.01" min="0" value="${p.price??''}"></div><div class="field"><label>Voorraad locatie 1</label><input name="stock" type="number" step="1" min="0" value="${p.stock??0}"></div><div class="field"><label>Minimumvoorraad</label><input name="minStock" type="number" step="1" min="0" value="${p.minStock??0}"></div><div class="field"><label>Magazijnlocatie</label><input name="warehouse" value="${esc(p.warehouse||'')}"></div><div class="field full"><label>Foto onderdeel</label><div class="photo-picker"><div class="photo-preview" id="photoPreview">${p.photo?`<img src="${p.photo}">`:'Klik op bestand<br>om foto toe te voegen'}</div><input name="photoFile" id="photoFile" type="file" accept="image/*"></div></div></div>`}
function initPartMachinePicker(){const select=$('#partMachineChoice'),field=$('#partNewMachineField'),input=$('#partNewMachine');if(!select||!field)return;const sync=()=>{const custom=select.value==='__new__';field.style.display=custom?'grid':'none';if(input)input.required=custom;if(custom&&input)setTimeout(()=>input.focus(),0)};select.onchange=sync;sync()}
function openPart(id){const old=state.parts.find(p=>p.id===id)||{};showModal(id?'Onderdeel bewerken':'Onderdeel toevoegen',partForm(old),'Opslaan',async fd=>{const file=fd.get('photoFile');let photo=old.photo||'';if(file&&file.size)photo=await compressImage(file);const machineChoice=val(fd,'deviceBrandChoice');const deviceBrand=machineChoice==='__new__'?val(fd,'deviceBrandNew'):machineChoice;if(machineChoice==='__new__'&&!deviceBrand){alert('Vul het nieuwe merk of de nieuwe machine in.');return}const obj={...old,id:old.id||uid('part'),artNr:val(fd,'artNr'),description:val(fd,'description'),deviceBrand,price:Number(fd.get('price')||0),stock:Number(fd.get('stock')||0),minStock:Number(fd.get('minStock')||0),supplierCode:val(fd,'supplierCode'),warehouse:val(fd,'warehouse'),photo,updatedAt:new Date().toISOString()};await put('parts',obj);closeModal();await refresh();toast('Onderdeel opgeslagen')});setTimeout(()=>{initPartMachinePicker();const f=$('#photoFile');if(f)f.onchange=async()=>{if(f.files[0])$('#photoPreview').innerHTML=`<img src="${await compressImage(f.files[0])}">`}},0)}'''

s=s[:start]+new_block+s[end:]

# Zoekfunctie: alleen Dashboard zoekt globaal. De andere tabbladen gebruiken
# dezelfde zoekbalk uitsluitend als filter binnen hun eigen gegevens.
s=s.replace(
    "function renderGlobalSearchResults(){\n const box=$('#globalSearchResults'),input=$('#globalSearch');if(!box||!input)return;",
    "function renderGlobalSearchResults(){\n if(state.view!=='dashboard'){closeGlobalSearch();return}\n const box=$('#globalSearchResults'),input=$('#globalSearch');if(!box||!input)return;",
    1
)

old_switch="function switchView(view){if(view==='settings'&&!window.machineparkIsAdmin)view='dashboard';state.view=view;$$('.view').forEach(v=>v.classList.remove('active'));$('#view-'+view).classList.add('active');$$('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const [t,s]=pageMeta(view);$('#pageTitle').textContent=t;$('#pageSubtitle').textContent=s;renderAll();if(view==='settings'&&window.machineparkIsAdmin)loadAdminPanels()}"
new_switch="""const machineparkViewQueries={dashboard:'',devices:'',maintenance:'',breakdowns:'',parts:''};
function configureSearchForView(view){const input=$('#globalSearch'),actions=document.querySelector('.top-actions');if(!input||!actions)return;if(view==='settings'){state.query='';input.value='';actions.style.display='none';closeGlobalSearch();return}actions.style.display='';state.query=machineparkViewQueries[view]||'';input.value=state.query;input.placeholder=({dashboard:'Zoek overal in Machinepark…',devices:'Zoek in toestellen…',maintenance:'Zoek in onderhoud…',breakdowns:'Zoek in depannages…',parts:'Zoek in onderdelen…'})[view]||'Zoeken…';if(view!=='dashboard')closeGlobalSearch()}
function switchView(view){if(view==='settings'&&!window.machineparkIsAdmin)view='dashboard';state.view=view;$$('.view').forEach(v=>v.classList.remove('active'));$('#view-'+view).classList.add('active');$$('.nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));const [t,s]=pageMeta(view);$('#pageTitle').textContent=t;$('#pageSubtitle').textContent=s;configureSearchForView(view);renderAll();if(view==='settings'&&window.machineparkIsAdmin)loadAdminPanels()}"""
if old_switch not in s:
    raise SystemExit('switchView niet gevonden voor zoekscope-patch')
s=s.replace(old_switch,new_switch,1)

old_bind="$('#globalSearch').oninput=e=>{state.query=e.target.value.trim();renderAll();renderGlobalSearchResults()};$('#globalSearch').onfocus=()=>{if(state.query)renderGlobalSearchResults()};$('#globalSearch').onkeydown=e=>{if(e.key==='Escape'){closeGlobalSearch();e.target.blur()}else if(e.key==='Enter'){const first=$('#globalSearchResults .global-search-result');if(first){e.preventDefault();first.click()}}};"
new_bind="$('#globalSearch').oninput=e=>{state.query=e.target.value.trim();if(state.view!=='settings')machineparkViewQueries[state.view]=state.query;renderAll();if(state.view==='dashboard')renderGlobalSearchResults();else closeGlobalSearch()};$('#globalSearch').onfocus=()=>{if(state.view==='dashboard'&&state.query)renderGlobalSearchResults()};$('#globalSearch').onkeydown=e=>{if(e.key==='Escape'){closeGlobalSearch();e.target.blur()}else if(e.key==='Enter'&&state.view==='dashboard'){const first=$('#globalSearchResults .global-search-result');if(first){e.preventDefault();first.click()}}};"
if old_bind not in s:
    raise SystemExit('globalSearch binding niet gevonden voor zoekscope-patch')
s=s.replace(old_bind,new_bind,1)

s=s.replace('v1.32 • Vereenvoudigde acties','v1.35 • Zoeken per tabblad',1)
s=s.replace('v1.33 • Machinekeuze onderdelen','v1.35 • Zoeken per tabblad',1)
s=s.replace('v1.34 • Onderdelenmerken apart','v1.35 • Zoeken per tabblad',1)
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
ws=sw.read_text(encoding='utf-8')
for old in ['machinepark-v1.32-simplified-actions','machinepark-v1.33-part-machine-picker','machinepark-v1.34-parts-machine-separate']:
    ws=ws.replace(old,'machinepark-v1.35-search-per-view')
sw.write_text(ws,encoding='utf-8')
