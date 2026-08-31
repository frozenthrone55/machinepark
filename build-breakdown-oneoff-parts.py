from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="breakdown-oneoff-parts-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Nieuwe locatie-depannage: neem de vrije, niet-voorraadgebonden onderdelen per toestel mee.
    old_selected = "usedParts:[...card.querySelectorAll('.breakdown-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0)}))"
    new_selected = "usedParts:[...card.querySelectorAll('.breakdown-device-usage-list .usage-row')].map(row=>({partId:row.querySelector('.usage-part')?.value||'',qty:Number(row.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0),oneOffParts:window.machineparkCollectBreakdownOneOff(card.querySelector('.breakdown-oneoff-parts'))}))"
    replace_once(old_selected, new_selected, 'eenmalige onderdelen per depannagetoestel verzamelen')

    # Bestaande depannage bewerken: bewaar de vrije onderdelen zonder voorraadmutatie.
    old_edit = "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,usedParts:usage,updatedAt:new Date().toISOString()};"
    new_edit = "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,usedParts:usage,oneOffParts:window.machineparkCollectBreakdownOneOff(document.querySelector('#modalForm .breakdown-oneoff-parts:not(.breakdown-oneoff-machine)')),updatedAt:new Date().toISOString()};"
    replace_once(old_edit, new_edit, 'eenmalige onderdelen bij depannage bewerken')

    # Nieuwe locatie-depannage: zet de verzamelde vrije onderdelen in elk afzonderlijk record.
    old_batch = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,workSessions,hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));"
    new_batch = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,workSessions,hours,usedParts:item.usedParts,oneOffParts:item.oneOffParts,createdAt:now,updatedAt:now}));"
    replace_once(old_batch, new_batch, 'eenmalige onderdelen bij nieuwe depannage opslaan')

    feature = r'''
<style data-machinepark-build-fix="breakdown-oneoff-parts-v1">
.breakdown-oneoff-parts{margin-top:12px;border-top:1px solid var(--line);padding-top:12px}
.breakdown-oneoff-parts .section-title{margin-bottom:3px}
.breakdown-oneoff-list{display:grid;gap:7px;margin-top:9px}
.breakdown-oneoff-head,.breakdown-oneoff-row{display:grid;grid-template-columns:minmax(145px,190px) minmax(220px,1fr) 42px;gap:8px;align-items:center}
.breakdown-oneoff-head{font-size:11px;font-weight:750;color:var(--muted);padding:0 2px}
.breakdown-oneoff-row input{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}
.breakdown-oneoff-machine{grid-column:1/-1}
.breakdown-machine-card:not(.selected) .breakdown-oneoff-parts{opacity:.75}
@media(max-width:650px){.breakdown-oneoff-head{display:none}.breakdown-oneoff-row{grid-template-columns:1fr 42px}.breakdown-oneoff-row .breakdown-oneoff-code,.breakdown-oneoff-row .breakdown-oneoff-description{grid-column:1}.breakdown-oneoff-row .breakdown-remove-oneoff{grid-column:2;grid-row:1/3}}
</style>
<script data-machinepark-build-fix="breakdown-oneoff-parts-v1">
(() => {
  const LIMIT = 30;
  const escAttr = value => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

  function normalize(items) {
    return (Array.isArray(items) ? items : []).map(item => ({
      supplierCode: String(item?.supplierCode || '').trim().slice(0, 120),
      description: String(item?.description || '').trim().slice(0, 300),
    })).filter(item => item.supplierCode || item.description).slice(0, LIMIT);
  }

  function rowHtml(item = {}, disabled = false) {
    const off = disabled ? ' disabled' : '';
    return `<div class="breakdown-oneoff-row"><input class="breakdown-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${escAttr(item.supplierCode || '')}"${off}><input class="breakdown-oneoff-description" type="text" maxlength="300" placeholder="Omschrijving" value="${escAttr(item.description || '')}"${off}><button type="button" class="remove-line breakdown-remove-oneoff" data-remove-breakdown-oneoff aria-label="Eenmalig onderdeel verwijderen"${off}>×</button></div>`;
  }

  function editorHtml(items = [], { machine = false, disabled = false } = {}) {
    const saved = normalize(items);
    const rows = saved.length ? saved : [{}];
    return `<div class="breakdown-oneoff-parts${machine ? ' breakdown-oneoff-machine' : ''}">
      <div class="section-title">Eenmalige onderdelen</div>
      <div class="muted" style="font-size:11px">Voor onderdelen die niet in de onderdelenlijst staan. Deze regels wijzigen de voorraad niet.</div>
      <div class="breakdown-oneoff-head"><span>Leveranciercode</span><span>Omschrijving</span><span></span></div>
      <div class="breakdown-oneoff-list">${rows.map(item => rowHtml(item, disabled)).join('')}</div>
      <button type="button" class="btn small breakdown-add-oneoff" data-add-breakdown-oneoff style="margin-top:8px"${disabled ? ' disabled' : ''}>+ Eenmalig onderdeel</button>
    </div>`;
  }

  window.machineparkCollectBreakdownOneOff = root => {
    if (!root) return [];
    return normalize([...root.querySelectorAll('.breakdown-oneoff-row')].map(row => ({
      supplierCode: row.querySelector('.breakdown-oneoff-code')?.value || '',
      description: row.querySelector('.breakdown-oneoff-description')?.value || '',
    })));
  };

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
    return insertBeforePhotoEditor(
      previousBreakdownForm(record),
      `<div class="field full">${editorHtml(record.oneOffParts || [])}</div>`
    );
  };

  const previousBreakdownMachineCardHtml = breakdownMachineCardHtml;
  breakdownMachineCardHtml = function(device) {
    return insertAfterStockParts(
      previousBreakdownMachineCardHtml(device),
      editorHtml([], { machine: true, disabled: true })
    );
  };

  const previousSetBreakdownMachineEnabled = setBreakdownMachineEnabled;
  setBreakdownMachineEnabled = function(card, enabled) {
    previousSetBreakdownMachineEnabled(card, enabled);
    card?.querySelectorAll('.breakdown-oneoff-code,.breakdown-oneoff-description,.breakdown-add-oneoff,.breakdown-remove-oneoff').forEach(el => el.disabled = !enabled);
  };

  document.addEventListener('click', event => {
    const add = event.target.closest?.('[data-add-breakdown-oneoff]');
    if (add) {
      const root = add.closest('.breakdown-oneoff-parts');
      const list = root?.querySelector('.breakdown-oneoff-list');
      if (!list) return;
      if (list.querySelectorAll('.breakdown-oneoff-row').length >= LIMIT) {
        toast(`Maximaal ${LIMIT} eenmalige onderdelen per depannage.`);
        return;
      }
      list.insertAdjacentHTML('beforeend', rowHtml({}, false));
      list.lastElementChild?.querySelector('.breakdown-oneoff-code')?.focus();
      return;
    }

    const remove = event.target.closest?.('[data-remove-breakdown-oneoff]');
    if (!remove) return;
    const root = remove.closest('.breakdown-oneoff-parts');
    const rows = root?.querySelectorAll('.breakdown-oneoff-row');
    const row = remove.closest('.breakdown-oneoff-row');
    if (!row) return;
    if (rows && rows.length > 1) row.remove();
    else row.querySelectorAll('input').forEach(input => input.value = '');
  });
})();
</script>
'''

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor eenmalige depannageonderdelen')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Eenmalige onderdelen',
    'Leveranciercode',
    'Omschrijving',
    'machineparkCollectBreakdownOneOff',
    'oneOffParts:item.oneOffParts',
    'oneOffParts:window.machineparkCollectBreakdownOneOff',
    'breakdown-oneoff-machine',
    'data-add-breakdown-oneoff',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: eenmalige depannageonderdelen ontbreken ({needle})')

print('[Machinepark] eenmalige depannageonderdelen met leveranciercode en omschrijving actief')
