from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="breakdown-location-hours-v2"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Toon de gezamenlijke werktijd ook in het depannage-overzicht.
    replace_once(
        '<thead><tr><th>Datum / uur</th><th>Toestel</th><th>Probleem</th><th>Prioriteit</th><th>Status</th><th>Technieker</th><th></th></tr></thead><tbody id="breakdownBody"></tbody>',
        '<thead><tr><th>Datum / uur</th><th>Toestel</th><th>Probleem</th><th>Prioriteit</th><th>Status</th><th>Technieker</th><th>Werkuren / toestellen</th><th></th></tr></thead><tbody id="breakdownBody"></tbody>',
        'depannage tabelkop',
    )

    # Werkuren horen bij de locatiebeurt, niet meer bij iedere toestelkaart.
    location_anchor = '<div id="breakdownLocationCount" class="muted" style="font-size:11px;margin-top:4px">Typ een locatie of toestelnummer. De zoeklijst wordt automatisch korter.</div></div><div class="field"><label>Datum melding *'
    location_hours = '<div id="breakdownLocationCount" class="muted" style="font-size:11px;margin-top:4px">Typ een locatie of toestelnummer. De zoeklijst wordt automatisch korter.</div></div><div class="field full"><label>Werkuren depannage *</label><input name="hours" type="number" min="0" step="0.25" required placeholder="bv. 2"><div class="muted" style="font-size:11px;margin-top:4px">Totale werktijd voor alle geselecteerde toestellen op deze locatie.</div></div><div class="field"><label>Datum melding *'
    replace_once(location_anchor, location_hours, 'werkuren bij locatie')

    replace_once(
        'Selecteer de toestellen waarop een depannage werd uitgevoerd. Probleem, diagnose, oplossing en onderdelen worden per toestel geregistreerd.',
        'Selecteer de toestellen waarop een depannage werd uitgevoerd. Werkuren, datum, uur en technieker gelden voor de volledige locatiebeurt; probleem, diagnose, oplossing, prioriteit, status en onderdelen blijven per toestel.',
        'uitleg locatie-depannage',
    )

    replace_once(
        '<div class="field"><label>Werkuren</label><input class="breakdown-machine-hours" type="number" min="0" step="0.25" disabled></div>',
        '',
        'werkuren per toestel',
    )

    replace_once(
        '.breakdown-machine-solution,.breakdown-machine-hours,.breakdown-add-usage',
        '.breakdown-machine-solution,.breakdown-add-usage',
        'werkuren-selector per toestel',
    )

    replace_once(
        "solution:card.querySelector('.breakdown-machine-solution')?.value.trim()||'',hours:Number(card.querySelector('.breakdown-machine-hours')?.value||0),usedParts:",
        "solution:card.querySelector('.breakdown-machine-solution')?.value.trim()||'',usedParts:",
        'werkuren uit geselecteerd toestel',
    )

    # Nieuwe locatie-depannage: één groeps-ID, gezamenlijke uren en de actuele groepsgrootte.
    replace_once(
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),now=new Date().toISOString();const records=items.map(item=>({id:uid('brk'),deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,hours:item.hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),hours=Number(fd.get('hours')||0),now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        'opslaan gezamenlijke depannage-uren',
    )

    # Bij bewerken van één toestel uit een groepsdepannage worden alle gedeelde velden
    # op de andere toestellen uit die registratie mee aangepast.
    replace_once(
        "await applyUsage(usage,old.usedParts||[]);await put('breakdowns',b);closeModal();await refresh();toast('Depannage opgeslagen')",
        "await applyUsage(usage,old.usedParts||[]);if(old.batchId){const groupSize=state.breakdowns.filter(x=>x.batchId===old.batchId).length,grouped={...b,batchSize:groupSize};await put('breakdowns',grouped);const siblings=state.breakdowns.filter(x=>x.batchId===old.batchId&&x.id!==old.id).map(x=>({...x,date:grouped.date,time:grouped.time,technician:grouped.technician,hours:grouped.hours,batchSize:groupSize,updatedAt:grouped.updatedAt}));if(siblings.length)await putMany('breakdowns',siblings)}else await put('breakdowns',b);closeModal();await refresh();toast('Depannage opgeslagen')",
        'gedeelde groepsvelden synchroniseren bij bewerken',
    )

    # Als één toestel uit een groepsdepannage wordt verwijderd, pas dan de resterende
    # toestelregistraties expliciet aan naar de nieuwe groepsgrootte.
    replace_once(
        "try{const result=await deleteServiceRecordAtomic(storeName,record);closeModal();await refresh();toast(`${kind==='onderhoud'?'Onderhoud':'Depannage'} verwijderd${result.restoredParts?` · ${result.restoredParts} onderdeel${result.restoredParts===1?'':'types'} terug op voorraad`:''}`)}catch(error)",
        "try{const result=await deleteServiceRecordAtomic(storeName,record);if(storeName==='breakdowns'&&record.batchId){const remaining=collection.filter(x=>x.batchId===record.batchId&&x.id!==record.id),batchSize=remaining.length,now=new Date().toISOString();if(remaining.length)await putMany('breakdowns',remaining.map(x=>({...x,batchSize,updatedAt:now})))}closeModal();await refresh();toast(`${kind==='onderhoud'?'Onderhoud':'Depannage'} verwijderd${result.restoredParts?` · ${result.restoredParts} onderdeel${result.restoredParts===1?'':'types'} terug op voorraad`:''}`)}catch(error)",
        'groepsgrootte synchroniseren bij verwijderen',
    )

    # Bij gegroepeerde registraties verduidelijkt het bewerkformulier dat de uren voor de hele depannage gelden.
    replace_once(
        '<div class="field"><label>Werkuren</label><input name="hours" type="number" min="0" step="0.25" value="${b.hours??\'\'}"></div>',
        '<div class="field"><label>${b.batchId?\'Werkuren depannage\':\'Werkuren\'}</label><input name="hours" type="number" min="0" step="0.25" value="${b.hours??\'\'}">${b.batchId?`<div class="muted" style="font-size:11px;margin-top:4px">Datum, uur, technieker en werkuren gelden voor de volledige depannagegroep · ${esc(breakdownWorkSummary(b))}</div>`:\'\'}</div>',
        'werkurenlabel bewerken',
    )

    # Formatteer 2 uur over 3 toestellen als: 2 u / 3 toestellen.
    # De live groepsgrootte uit state heeft voorrang, zodat ook herstel/undo correct wordt weergegeven.
    helper_anchor = 'function renderBreakdowns(){'
    helper = '''function breakdownWorkSummary(b){const hours=Number(b?.hours||0);if(!Number.isFinite(hours)||hours<=0)return '—';const liveCount=b?.batchId?state.breakdowns.filter(x=>x.batchId===b.batchId).length:0;const count=b?.batchId?Math.max(1,liveCount||Number(b.batchSize||0)):1;const hourText=hours.toLocaleString('nl-BE',{maximumFractionDigits:2});return `${hourText} u / ${count} ${count===1?'toestel':'toestellen'}`}
function renderBreakdowns(){'''
    replace_once(helper_anchor, helper, 'werkurensamenvatting')

    replace_once(
        "<td>${esc(b.technician||'—')}</td><td><button class=\"btn small\" data-edit-breakdown=\"${b.id}\">Details</button></td>",
        "<td>${esc(b.technician||'—')}</td><td class=\"nowrap\">${esc(breakdownWorkSummary(b))}</td><td><button class=\"btn small\" data-edit-breakdown=\"${b.id}\">Details</button></td>",
        'werkurenkolom depannages',
    )

    replace_once(
        '<tr><td colspan="7"><div class="empty">Nog geen depannages geregistreerd.</div></td></tr>',
        '<tr><td colspan="8"><div class="empty">Nog geen depannages geregistreerd.</div></td></tr>',
        'lege depannagetabel',
    )

    # Het individuele depannageverslag gebruikt dezelfde groepsnotatie.
    replace_once(
        "servicePrintField('Werkuren', Number(record.hours || 0) ? `${Number(record.hours)} uur` : '—'),",
        "servicePrintField('Werkuren / toestellen', breakdownWorkSummary(record)),",
        'werkuren op depannage-afdruk',
    )

    # Markering zonder runtime-code: alle wijzigingen hierboven zijn direct in de gebouwde HTML verwerkt.
    index = index.replace('</body>', f'<span {MARKER} hidden></span></body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Werkuren depannage *',
    'Totale werktijd voor alle geselecteerde toestellen op deze locatie.',
    "batchId=uid('brkbatch'),batchSize=items.length",
    'batchSize=remaining.length',
    'date:grouped.date,time:grouped.time,technician:grouped.technician,hours:grouped.hours',
    'function breakdownWorkSummary',
    'Werkuren / toestellen',
    "servicePrintField('Werkuren / toestellen', breakdownWorkSummary(record))",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: locatie-uren depannage ontbreken ({needle})')

if 'breakdown-machine-hours' in index:
    raise SystemExit('Buildvalidatie mislukt: werkuren per toestel zijn nog aanwezig')

print('[Machinepark] depannage-uren en gedeelde groepsvelden per locatiebeurt actief')
