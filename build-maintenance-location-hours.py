from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="maintenance-location-hours-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Toon de gezamenlijke werktijd in het onderhoudsoverzicht.
    replace_once(
        '<thead><tr><th>Datum / uur</th><th>Toestel</th><th>Type</th><th>Technieker</th><th>Onderdelen</th><th>Notitie</th><th></th></tr></thead><tbody id="maintenanceBody"></tbody>',
        '<thead><tr><th>Datum / uur</th><th>Toestel</th><th>Type</th><th>Technieker</th><th>Werkuren / toestellen</th><th>Onderdelen</th><th>Notitie</th><th></th></tr></thead><tbody id="maintenanceBody"></tbody>',
        'onderhoud tabelkop',
    )

    # Werkuren horen bij de volledige onderhoudsbeurt op de locatie.
    location_anchor = '<div id="maintenanceLocationCount" class="muted" style="font-size:11px;margin-top:4px">Typ een locatie of toestelnummer. De zoeklijst wordt automatisch korter.</div></div><div class="field"><label>Datum *'
    location_hours = '<div id="maintenanceLocationCount" class="muted" style="font-size:11px;margin-top:4px">Typ een locatie of toestelnummer. De zoeklijst wordt automatisch korter.</div></div><div class="field full"><label>Werkuren onderhoud *</label><input name="hours" type="number" min="0" step="0.25" required placeholder="bv. 2"><div class="muted" style="font-size:11px;margin-top:4px">Totale werktijd voor alle geselecteerde toestellen op deze locatie.</div></div><div class="field"><label>Datum *'
    replace_once(location_anchor, location_hours, 'werkuren bij onderhoudslocatie')

    replace_once(
        'Selecteer de toestellen waarop onderhoud is uitgevoerd. Type, werkzaamheden en onderdelen worden per toestel geregistreerd.',
        'Selecteer de toestellen waarop onderhoud is uitgevoerd. De werkuren gelden voor de volledige locatiebeurt; type, werkzaamheden en onderdelen blijven per toestel.',
        'uitleg locatie-onderhoud',
    )

    # Ook bij het later bewerken van een onderhoudsregistratie zijn werkuren zichtbaar.
    replace_once(
        '<div class="field"><label>Technieker</label><input name="technician" value="${esc(m.technician||\'\')}"></div><div class="field full"><label>Uitgevoerde werkzaamheden / notitie</label>',
        '<div class="field"><label>Technieker</label><input name="technician" value="${esc(m.technician||\'\')}"></div><div class="field"><label>${m.batchId?\'Werkuren onderhoud\':\'Werkuren\'}</label><input name="hours" type="number" min="0" step="0.25" value="${m.hours??\'\'}">${m.batchId?`<div class="muted" style="font-size:11px;margin-top:4px">Deze uren gelden voor de volledige onderhoudsgroep · ${esc(maintenanceWorkSummary(m))}</div>`:\'\'}</div><div class="field full"><label>Uitgevoerde werkzaamheden / notitie</label>',
        'werkuren in onderhoud bewerkformulier',
    )

    # Nieuwe locatiebeurt: één urenwaarde en één groeps-ID voor alle toestelregistraties.
    replace_once(
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),now=new Date().toISOString();const records=items.map(item=>({id:uid('mnt'),deviceId:item.deviceId,type:item.type,date,time,technician,notes:item.notes,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),hours=Number(fd.get('hours')||0),now=new Date().toISOString(),batchId=uid('mntbatch');const records=items.map(item=>({id:uid('mnt'),batchId,deviceId:item.deviceId,type:item.type,date,time,technician,hours,notes:item.notes,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        'opslaan gezamenlijke onderhoudsuren',
    )

    # Bij bewerken blijven de gedeelde gegevens van dezelfde onderhoudsbeurt gelijk.
    replace_once(
        "const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),notes:val(fd,'notes'),usedParts:usage,updatedAt:new Date().toISOString()};await applyUsage(usage,old.usedParts||[]);await put('maintenance',m);closeModal();await refresh();toast('Onderhoud gewijzigd')",
        "const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),hours:Number(fd.get('hours')||0),notes:val(fd,'notes'),usedParts:usage,updatedAt:new Date().toISOString()};await applyUsage(usage,old.usedParts||[]);await put('maintenance',m);if(old.batchId){const siblings=state.maintenance.filter(x=>x.batchId===old.batchId&&x.id!==old.id).map(x=>({...x,date:m.date,time:m.time,technician:m.technician,hours:m.hours,updatedAt:m.updatedAt}));if(siblings.length)await putMany('maintenance',siblings)}closeModal();await refresh();toast('Onderhoud gewijzigd')",
        'onderhoudsgroep synchroniseren bij bewerken',
    )

    # Formatteer bijvoorbeeld 2 uur over 3 toestellen als 2 u / 3 toestellen.
    helper_anchor = 'function renderMaintenance(){'
    helper = '''function maintenanceWorkSummary(m){const hours=Number(m?.hours||0);if(!Number.isFinite(hours)||hours<=0)return '—';const count=m?.batchId?Math.max(1,state.maintenance.filter(x=>x.batchId===m.batchId).length):1;const hourText=hours.toLocaleString('nl-BE',{maximumFractionDigits:2});return `${hourText} u / ${count} ${count===1?'toestel':'toestellen'}`}
function renderMaintenance(){'''
    replace_once(helper_anchor, helper, 'onderhoud werkurensamenvatting')

    replace_once(
        "<td>${esc(m.technician||'—')}</td><td>${esc(usedPartsText(m.usedParts))}</td><td>${esc(m.notes||'—')}</td><td><button class=\"btn small\" data-maintenance-details=\"${m.id}\">Details</button></td>",
        "<td>${esc(m.technician||'—')}</td><td class=\"nowrap\">${esc(maintenanceWorkSummary(m))}</td><td>${esc(usedPartsText(m.usedParts))}</td><td>${esc(m.notes||'—')}</td><td><button class=\"btn small\" data-maintenance-details=\"${m.id}\">Details</button></td>",
        'werkurenkolom onderhoud',
    )

    replace_once(
        '<tr><td colspan="7"><div class="empty">Nog geen onderhoud geregistreerd.</div></td></tr>',
        '<tr><td colspan="8"><div class="empty">Nog geen onderhoud geregistreerd.</div></td></tr>',
        'lege onderhoudstabel',
    )

    # Detailvenster toont dezelfde groepsnotatie; na verwijderen wordt dit dynamisch opnieuw berekend.
    replace_once(
        '<div class="field"><label>Technieker</label><div>${esc(m.technician||\'—\')}</div></div><div class="field full"><label>Gebruikte onderdelen</label>',
        '<div class="field"><label>Technieker</label><div>${esc(m.technician||\'—\')}</div></div><div class="field"><label>Werkuren / toestellen</label><div>${esc(maintenanceWorkSummary(m))}</div></div><div class="field full"><label>Gebruikte onderdelen</label>',
        'werkuren in onderhoud details',
    )

    # Het individuele onderhoudsverslag gebruikt dezelfde groepsnotatie.
    print_old = "servicePrintField('Type onderhoud', record.type || '—'),\n          servicePrintField('Toestel', serviceRecordDevice(record), true),\n          servicePrintField('Technieker', record.technician || '—'),\n          servicePrintField('Gebruikte onderdelen', serviceRecordParts(record), true),"
    print_new = "servicePrintField('Type onderhoud', record.type || '—'),\n          servicePrintField('Toestel', serviceRecordDevice(record), true),\n          servicePrintField('Technieker', record.technician || '—'),\n          servicePrintField('Werkuren / toestellen', maintenanceWorkSummary(record)),\n          servicePrintField('Gebruikte onderdelen', serviceRecordParts(record), true),"
    replace_once(print_old, print_new, 'werkuren op onderhoudsafdruk')

    # Markering zonder runtime-code; de wijzigingen zijn rechtstreeks in de gebouwde HTML toegepast.
    index = index.replace('</body>', f'<span {MARKER} hidden></span></body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Werkuren onderhoud *',
    'Totale werktijd voor alle geselecteerde toestellen op deze locatie.',
    "batchId=uid('mntbatch')",
    'function maintenanceWorkSummary',
    'Werkuren / toestellen',
    "servicePrintField('Werkuren / toestellen', maintenanceWorkSummary(record))",
    "state.maintenance.filter(x=>x.batchId===old.batchId&&x.id!==old.id)",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: locatie-uren onderhoud ontbreken ({needle})')

print('[Machinepark] onderhoudsuren per locatiebeurt actief')
