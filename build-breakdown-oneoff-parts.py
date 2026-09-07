from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="service-oneoff-parts-v2"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Depannage: vrije onderdelen per toestel verzamelen en bewaren.
    replace_once(
        "usedParts:[...card.querySelectorAll('.breakdown-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0)}))",
        "usedParts:[...card.querySelectorAll('.breakdown-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0),oneOffParts:window.machineparkCollectServiceOneOff(card.querySelector('.service-oneoff-parts'))}))",
        'eenmalige onderdelen per depannagetoestel verzamelen',
    )
    replace_once(
        "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,usedParts:usage,updatedAt:new Date().toISOString()};",
        "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,usedParts:usage,oneOffParts:window.machineparkCollectServiceOneOff(document.querySelector('#modalForm .service-oneoff-parts:not(.service-oneoff-machine)')),updatedAt:new Date().toISOString()};",
        'eenmalige onderdelen bij depannage bewerken',
    )
    replace_once(
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,workSessions,hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,workSessions,hours,usedParts:item.usedParts,oneOffParts:item.oneOffParts,createdAt:now,updatedAt:now}));",
        'eenmalige onderdelen bij nieuwe depannage opslaan',
    )

    # Onderhoud: dezelfde vrije onderdelen per toestel verzamelen en bewaren.
    replace_once(
        "usedParts:[...card.querySelectorAll('.maintenance-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0)}))",
        "usedParts:[...card.querySelectorAll('.maintenance-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0),oneOffParts:window.machineparkCollectServiceOneOff(card.querySelector('.service-oneoff-parts'))}))",
        'eenmalige onderdelen per onderhoudstoestel verzamelen',
    )
    replace_once(
        "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,notes:val(fd,'notes'),usedParts:usage,updatedAt:new Date().toISOString()};",
        "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,notes:val(fd,'notes'),usedParts:usage,oneOffParts:window.machineparkCollectServiceOneOff(document.querySelector('#modalForm .service-oneoff-parts:not(.service-oneoff-machine)')),updatedAt:new Date().toISOString()};",
        'eenmalige onderdelen bij onderhoud bewerken',
    )
    replace_once(
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('mntbatch');const records=items.map(item=>({id:uid('mnt'),batchId,deviceId:item.deviceId,type:item.type,date,time,technician,workSessions,hours,notes:item.notes,usedParts:item.usedParts,createdAt:now,updatedAt:now}));",
        "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('mntbatch');const records=items.map(item=>({id:uid('mnt'),batchId,deviceId:item.deviceId,type:item.type,date,time,technician,workSessions,hours,notes:item.notes,usedParts:item.usedParts,oneOffParts:item.oneOffParts,createdAt:now,updatedAt:now}));",
        'eenmalige onderdelen bij nieuw onderhoud opslaan',
    )

    # Onderhoudsdetails krijgen de vrije onderdelen zonder extra wrapper rond showMaintenanceDetails.
    replace_once(
        '<div class="field full"><label>Gebruikte onderdelen</label><div>${esc(usedPartsText(m.usedParts))}</div></div>',
        '<div class="field full"><label>Gebruikte onderdelen</label><div>${esc(usedPartsText(m.usedParts))}</div></div>${window.machineparkOneOffMaintenanceDetailsHtml?window.machineparkOneOffMaintenanceDetailsHtml(m):\'\'}',
        'eenmalige onderdelen in onderhoudsdetails',
    )

    feature = r'''
<style data-machinepark-build-fix="service-oneoff-parts-v2">
.service-oneoff-parts{margin-top:12px;border-top:1px solid var(--line);padding-top:12px}
.service-oneoff-parts .section-title{margin-bottom:3px}
.service-oneoff-list{display:grid;gap:7px;margin-top:9px}
.service-oneoff-head,.service-oneoff-row{display:grid;grid-template-columns:minmax(135px,180px) minmax(200px,1fr) 90px 42px;gap:8px;align-items:center}
.service-oneoff-head{font-size:11px;font-weight:750;color:var(--muted);padding:0 2px}
.service-oneoff-row input{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}
.service-oneoff-machine{grid-column:1/-1}
.maintenance-machine-card:not(.selected) .service-oneoff-parts{opacity:.75}
.service-oneoff-detail-list{display:grid;gap:5px;margin-top:4px}
.service-oneoff-detail-row{font-size:13px;line-height:1.5;padding:5px 0;border-bottom:1px solid #e7ece9;overflow-wrap:anywhere}
.service-oneoff-detail-row:last-child{border-bottom:0}
@media(max-width:650px){
  .service-oneoff-head{display:none}
  .service-oneoff-row{grid-template-columns:1fr 90px 42px}
  .service-oneoff-code,.service-oneoff-description{grid-column:1}
  .service-oneoff-qty{grid-column:2;grid-row:1/3}
  .service-oneoff-remove{grid-column:3;grid-row:1/3}
}
</style>
<script data-machinepark-build-fix="service-oneoff-parts-v2">
(() => {
  const LIMIT = 30;
  const escAttr = value => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  function normalize(items) {
    return (Array.isArray(items) ? items : []).map(item => ({
      supplierCode: String(item?.supplierCode || '').trim().slice(0, 120),
      description: String(item?.description || '').trim().slice(0, 300),
      qty: Math.max(1, Math.min(999999, Math.round(Number(item?.qty) || 1))),
    })).filter(item => item.supplierCode || item.description).slice(0, LIMIT);
  }

  function displayLines(record) {
    return normalize(record?.oneOffParts).map(item => {
      const text = [item.supplierCode, item.description].filter(Boolean).join(' · ');
      return `${item.qty} × ${text}`;
    });
  }

  function rowHtml(item = {}, disabled = false) {
    const normalized = normalize([item])[0] || { supplierCode:'', description:'', qty:1 };
    const off = disabled ? ' disabled' : '';
    return `<div class="service-oneoff-row"><input class="service-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${escAttr(normalized.supplierCode)}"${off}><input class="service-oneoff-description" type="text" maxlength="300" placeholder="Omschrijving" value="${escAttr(normalized.description)}"${off}><input class="service-oneoff-qty" type="number" min="1" step="1" inputmode="numeric" aria-label="Aantal" value="${normalized.qty}"${off}><button type="button" class="remove-line service-oneoff-remove" data-remove-service-oneoff aria-label="Eenmalig onderdeel verwijderen"${off}>×</button></div>`;
  }

  function editorHtml(items = [], { machine = false, disabled = false, kind = 'service' } = {}) {
    const saved = normalize(items);
    const rows = saved.length ? saved : [{}];
    return `<div class="service-oneoff-parts${machine ? ' service-oneoff-machine' : ''}" data-oneoff-kind="${escAttr(kind)}">
      <div class="section-title">Eenmalige onderdelen</div>
      <div class="muted" style="font-size:11px">Voor onderdelen die niet in de onderdelenlijst staan. Deze regels wijzigen de voorraad niet.</div>
      <div class="service-oneoff-head"><span>Leveranciercode</span><span>Omschrijving</span><span>Aantal</span><span></span></div>
      <div class="service-oneoff-list">${rows.map(item => rowHtml(item, disabled)).join('')}</div>
      <button type="button" class="btn small service-oneoff-add" data-add-service-oneoff style="margin-top:8px"${disabled ? ' disabled' : ''}>+ Eenmalig onderdeel</button>
    </div>`;
  }

  window.machineparkCollectServiceOneOff = root => {
    if (!root) return [];
    return normalize([...root.querySelectorAll('.service-oneoff-row')].map(row => ({
      supplierCode: row.querySelector('.service-oneoff-code')?.value || '',
      description: row.querySelector('.service-oneoff-description')?.value || '',
      qty: row.querySelector('.service-oneoff-qty')?.value || 1,
    })));
  };
  window.machineparkCollectBreakdownOneOff = window.machineparkCollectServiceOneOff;

  function insertBeforePhotoEditor(html, block) {
    const photoMarker = '<div class="field full service-photo-editor">';
    const photoPos = html.indexOf(photoMarker);
    if (photoPos >= 0) return html.slice(0, photoPos) + block + html.slice(photoPos);
    const pos = html.lastIndexOf('</div>');
    return pos < 0 ? html + block : html.slice(0, pos) + block + html.slice(pos);
  }

  function insertAfterStockParts(html, block) {
    const marker = '+ Onderdeelregel</button>';
    const markerPos = html.indexOf(marker);
    if (markerPos < 0) return insertBeforePhotoEditor(html, block);
    const closePos = html.indexOf('</div>', markerPos + marker.length);
    if (closePos < 0) return insertBeforePhotoEditor(html, block);
    const insertPos = closePos + 6;
    return html.slice(0, insertPos) + block + html.slice(insertPos);
  }

  const previousBreakdownForm = breakdownForm;
  breakdownForm = function(record = {}) {
    return insertBeforePhotoEditor(previousBreakdownForm(record), `<div class="field full">${editorHtml(record.oneOffParts || [], { kind:'breakdown' })}</div>`);
  };

  const previousMaintenanceForm = maintenanceForm;
  maintenanceForm = function(record = {}) {
    return insertBeforePhotoEditor(previousMaintenanceForm(record), `<div class="field full">${editorHtml(record.oneOffParts || [], { kind:'maintenance' })}</div>`);
  };

  const previousBreakdownMachineCardHtml = breakdownMachineCardHtml;
  breakdownMachineCardHtml = function(device) {
    return insertAfterStockParts(previousBreakdownMachineCardHtml(device), editorHtml([], { machine:true, disabled:true, kind:'breakdown' }));
  };

  const previousMaintenanceMachineCardHtml = maintenanceMachineCardHtml;
  maintenanceMachineCardHtml = function(device) {
    return insertAfterStockParts(previousMaintenanceMachineCardHtml(device), editorHtml([], { machine:true, disabled:true, kind:'maintenance' }));
  };

  const previousSetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    previousSetBreakdownMachineEnabled(card, enabled);
    card?.querySelectorAll('.service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove').forEach(el => el.disabled = !enabled);
  };

  const previousSetMaintenanceMachineEnabled = setMaintenanceMachineEnabled;
  setMaintenanceMachineEnabled = function(card, enabled) {
    previousSetMaintenanceMachineEnabled(card, enabled);
    card?.querySelectorAll('.service-oneoff-code,.service-oneoff-description,.service-oneoff-qty,.service-oneoff-add,.service-oneoff-remove').forEach(el => el.disabled = !enabled);
  };

  function detailRowsHtml(record) {
    const lines = displayLines(record);
    return lines.map(line => `<div class="service-oneoff-detail-row">${escAttr(line)}</div>`).join('');
  }

  window.machineparkOneOffMaintenanceDetailsHtml = record => {
    const rows = detailRowsHtml(record);
    if (!rows) return '';
    return `<div class="field full" data-maintenance-oneoff-details><label>Eenmalige onderdelen</label><div class="service-oneoff-detail-list">${rows}</div></div>`;
  };

  function oneOffBreakdownDetailsHtml(record) {
    const rows = detailRowsHtml(record);
    if (!rows) return '';
    return `<div class="breakdown-detail-field full" data-breakdown-oneoff-details><label>Eenmalige onderdelen</label><div class="service-oneoff-detail-list">${rows}</div></div>`;
  }

  const previousShowBreakdownDetails = window.machineparkShowBreakdownDetails;
  if (typeof previousShowBreakdownDetails === 'function') {
    window.machineparkShowBreakdownDetails = function(id) {
      const result = previousShowBreakdownDetails(id);
      setTimeout(() => {
        const record = state.breakdowns.find(item => item.id === id);
        const html = record ? oneOffBreakdownDetailsHtml(record) : '';
        if (!html) return;
        const summary = document.querySelector('#modal .breakdown-detail-summary');
        if (!summary || summary.querySelector('[data-breakdown-oneoff-details]')) return;
        const usedPartsField = [...summary.querySelectorAll('.breakdown-detail-field')].find(field => field.querySelector('label')?.textContent.trim() === 'Gebruikte onderdelen');
        if (usedPartsField) usedPartsField.insertAdjacentHTML('afterend', html);
        else summary.insertAdjacentHTML('beforeend', html);
      }, 0);
      return result;
    };
  }

  function recordFor(kind, id) {
    const list = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    return list.find(item => item.id === id);
  }

  function injectOneOffPrint(kind, id) {
    const lines = displayLines(recordFor(kind, id));
    if (!lines.length) return;
    const grid = document.querySelector('#servicePrintSheet .service-print-grid');
    if (!grid || grid.querySelector('[data-print-oneoff-parts]')) return;
    const field = document.createElement('div');
    field.className = 'service-print-field full';
    field.dataset.printOneoffParts = '1';
    field.innerHTML = `<div class="service-print-label">Eenmalige onderdelen</div><div class="service-print-value">${escAttr(lines.join(String.fromCharCode(10)))}</div>`;
    const usedPartsField = [...grid.querySelectorAll('.service-print-field')].find(item => item.querySelector('.service-print-label')?.textContent.trim() === 'Gebruikte onderdelen');
    if (usedPartsField) usedPartsField.insertAdjacentElement('afterend', field);
    else grid.appendChild(field);
  }

  const previousPrintServiceRecord = window.printMachineparkServiceRecord;
  if (typeof previousPrintServiceRecord === 'function') {
    window.printMachineparkServiceRecord = function(kind, id) {
      if (kind !== 'breakdowns' && kind !== 'maintenance') return previousPrintServiceRecord(kind, id);
      const nativePrint = window.print;
      window.print = function() {
        try { injectOneOffPrint(kind, id); }
        finally { window.print = nativePrint; }
        return nativePrint.call(window);
      };
      try { return previousPrintServiceRecord(kind, id); }
      finally { if (window.print !== nativePrint) window.print = nativePrint; }
    };
  }

  document.addEventListener('click', event => {
    const add = event.target.closest?.('[data-add-service-oneoff]');
    if (add) {
      const root = add.closest('.service-oneoff-parts');
      const list = root?.querySelector('.service-oneoff-list');
      if (!list) return;
      if (list.querySelectorAll('.service-oneoff-row').length >= LIMIT) {
        const label = root.dataset.oneoffKind === 'maintenance' ? 'onderhoud' : 'depannage';
        toast(`Maximaal ${LIMIT} eenmalige onderdelen per ${label}.`);
        return;
      }
      list.insertAdjacentHTML('beforeend', rowHtml({}, false));
      list.lastElementChild?.querySelector('.service-oneoff-code')?.focus();
      return;
    }

    const remove = event.target.closest?.('[data-remove-service-oneoff]');
    if (!remove) return;
    const root = remove.closest('.service-oneoff-parts');
    const rows = root?.querySelectorAll('.service-oneoff-row');
    const row = remove.closest('.service-oneoff-row');
    if (!row) return;
    if (rows && rows.length > 1) row.remove();
    else {
      row.querySelector('.service-oneoff-code').value = '';
      row.querySelector('.service-oneoff-description').value = '';
      row.querySelector('.service-oneoff-qty').value = '1';
    }
  });
})();
</script>
'''

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor eenmalige serviceonderdelen')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Eenmalige onderdelen',
    'Leveranciercode',
    'Omschrijving',
    'Aantal',
    'service-oneoff-qty',
    'machineparkCollectServiceOneOff',
    'oneOffParts:item.oneOffParts',
    'maintenance-device-usage-list',
    'breakdown-device-usage-list',
    'previousMaintenanceForm',
    'previousMaintenanceMachineCardHtml',
    'data-maintenance-oneoff-details',
    'data-breakdown-oneoff-details',
    'injectOneOffPrint',
    "kind !== 'breakdowns' && kind !== 'maintenance'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: eenmalige serviceonderdelen ontbreken ({needle})')

print('[Machinepark] eenmalige onderdelen met aantal actief in depannages en onderhoud')
