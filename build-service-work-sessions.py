from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="service-work-sessions-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Nieuwe locatiebeurten: vervang het ene totaalveld door meerdere datum/duur-regels.
    breakdown_old = '<div class="field full"><label>Werkminuten depannage *</label><input name="hours" type="number" min="0" step="1" required placeholder="bv. 120"><div class="muted" style="font-size:11px;margin-top:4px">Totale werktijd voor alle geselecteerde toestellen op deze locatie.</div></div>'
    maintenance_old = '<div class="field full"><label>Werkminuten onderhoud *</label><input name="hours" type="number" min="0" step="1" required placeholder="bv. 120"><div class="muted" style="font-size:11px;margin-top:4px">Totale werktijd voor alle geselecteerde toestellen op deze locatie.</div></div>'
    session_new = '<div class="field full service-work-sessions" data-service-work-sessions><label>Werkdagen en tijd *</label><input name="hours" type="hidden" value="0"><div class="service-work-session-list" data-service-work-session-list><div class="service-work-session-row"><input type="date" name="workSessionDate" required aria-label="Datum werkdag"><input type="number" name="workSessionMinutes" min="1" step="1" required placeholder="minuten" aria-label="Werkduur in minuten"><button type="button" class="remove-line" data-remove-work-session aria-label="Werkdag verwijderen">×</button></div></div><div class="service-work-session-actions"><button type="button" class="btn small" data-add-work-session>+ Dag toevoegen</button><strong data-service-work-total>Totaal: 0 min</strong></div><div class="muted" style="font-size:11px">Voeg voor iedere depannage- of onderhoudsdag een aparte datum en werkduur toe. Het overzicht toont automatisch de totale tijd.</div></div>'
    replace_once(breakdown_old, session_new, 'meerdaagse depannagetijd')
    replace_once(maintenance_old, session_new, 'meerdaagse onderhoudstijd')

    # Bij bewerken hetzelfde meerdaagse blok tonen. Oude registraties worden als één regel aangeboden.
    breakdown_edit_old = '<div class="field"><label>${b.batchId?\'Werkminuten depannage\':\'Werkminuten\'}</label><input name="hours" type="number" min="0" step="1" value="${Number(b.hours||0)>0?Math.round(Number(b.hours)*60):\'\'}">${b.batchId?`<div class="muted" style="font-size:11px;margin-top:4px">Deze minuten gelden voor de volledige depannagegroep · ${esc(breakdownWorkSummary(b))}</div>`:\'\'}</div>'
    maintenance_edit_old = '<div class="field"><label>${m.batchId?\'Werkminuten onderhoud\':\'Werkminuten\'}</label><input name="hours" type="number" min="0" step="1" value="${Number(m.hours||0)>0?Math.round(Number(m.hours)*60):\'\'}">${m.batchId?`<div class="muted" style="font-size:11px;margin-top:4px">Deze minuten gelden voor de volledige onderhoudsgroep · ${esc(maintenanceWorkSummary(m))}</div>`:\'\'}</div>'
    replace_once(breakdown_edit_old, '${window.machineparkServiceWorkSessionsEditor(b,\'breakdown\')}', 'meerdaagse depannagetijd bij bewerken')
    replace_once(maintenance_edit_old, '${window.machineparkServiceWorkSessionsEditor(m,\'maintenance\')}', 'meerdaagse onderhoudstijd bij bewerken')

    # Verzamel sessies bij opslaan en behoud hours als compatibele totaalsom in uren.
    breakdown_edit_anchor = "const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),hours:Number(fd.get('hours')||0)/60,usedParts:usage,updatedAt:new Date().toISOString()};"
    breakdown_edit_new = "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const b={...old,deviceId:val(fd,'deviceId'),date:val(fd,'date'),time:val(fd,'time'),priority:val(fd,'priority'),status:val(fd,'status'),issue:val(fd,'issue'),diagnosis:val(fd,'diagnosis'),solution:val(fd,'solution'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,usedParts:usage,updatedAt:new Date().toISOString()};"
    replace_once(breakdown_edit_anchor, breakdown_edit_new, 'sessies opslaan bij depannage bewerken')

    breakdown_batch_anchor = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),hours=Number(fd.get('hours')||0)/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));"
    breakdown_batch_new = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('brkbatch'),batchSize=items.length;const records=items.map(item=>({id:uid('brk'),batchId,batchSize,deviceId:item.deviceId,date,time,priority:item.priority,status:item.status,issue:item.issue,diagnosis:item.diagnosis,solution:item.solution,technician,workSessions,hours,usedParts:item.usedParts,createdAt:now,updatedAt:now}));"
    replace_once(breakdown_batch_anchor, breakdown_batch_new, 'sessies opslaan bij nieuwe depannage')

    maintenance_edit_anchor = "const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),hours:Number(fd.get('hours')||0)/60,notes:val(fd,'notes'),usedParts:usage,updatedAt:new Date().toISOString()};"
    maintenance_edit_new = "const workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);const m={...old,deviceId:val(fd,'deviceId'),type:val(fd,'type'),date:val(fd,'date'),time:val(fd,'time'),technician:val(fd,'technician'),workSessions,hours:totalMinutes/60,notes:val(fd,'notes'),usedParts:usage,updatedAt:new Date().toISOString()};"
    replace_once(maintenance_edit_anchor, maintenance_edit_new, 'sessies opslaan bij onderhoud bewerken')

    maintenance_batch_anchor = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),hours=Number(fd.get('hours')||0)/60,now=new Date().toISOString(),batchId=uid('mntbatch');const records=items.map(item=>({id:uid('mnt'),batchId,deviceId:item.deviceId,type:item.type,date,time,technician,hours,notes:item.notes,usedParts:item.usedParts,createdAt:now,updatedAt:now}));"
    maintenance_batch_new = "const date=val(fd,'date'),time=val(fd,'time'),technician=val(fd,'technician'),workSessions=window.machineparkCollectWorkSessions(fd),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0),hours=totalMinutes/60,now=new Date().toISOString(),batchId=uid('mntbatch');const records=items.map(item=>({id:uid('mnt'),batchId,deviceId:item.deviceId,type:item.type,date,time,technician,workSessions,hours,notes:item.notes,usedParts:item.usedParts,createdAt:now,updatedAt:now}));"
    replace_once(maintenance_batch_anchor, maintenance_batch_new, 'sessies opslaan bij nieuw onderhoud')

    # Gedeelde locatiebeurten houden ook bij latere bewerking dezelfde sessies.
    index = index.replace('technician:grouped.technician,hours:grouped.hours,batchSize:groupSize', 'technician:grouped.technician,workSessions:grouped.workSessions,hours:grouped.hours,batchSize:groupSize', 1)
    index = index.replace('technician:m.technician,hours:m.hours,updatedAt:m.updatedAt', 'technician:m.technician,workSessions:m.workSessions,hours:m.hours,updatedAt:m.updatedAt', 1)

    # Afdrukken: naast de totaaltijd ook de afzonderlijke dagen tonen.
    index = index.replace("servicePrintField('Werkminuten / toestellen', breakdownWorkSummary(record)),", "servicePrintField('Werkminuten / toestellen', breakdownWorkSummary(record)),\n          servicePrintField('Werkdagen', window.machineparkServiceWorkSessionsText(record), true),", 1)
    index = index.replace("servicePrintField('Werkminuten / toestellen', maintenanceWorkSummary(record)),", "servicePrintField('Werkminuten / toestellen', maintenanceWorkSummary(record)),\n          servicePrintField('Werkdagen', window.machineparkServiceWorkSessionsText(record), true),", 1)

    feature = r'''
<style data-machinepark-build-fix="service-work-sessions-v1">
.service-work-sessions{border:1px solid var(--line);border-radius:12px;padding:12px;background:#f9fbfa}.service-work-session-list{display:grid;gap:8px}.service-work-session-row{display:grid;grid-template-columns:minmax(150px,1fr) minmax(130px,1fr) 42px;gap:8px;align-items:center}.service-work-session-row input{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}.service-work-session-actions{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-top:9px;flex-wrap:wrap}.service-work-session-actions strong{font-size:13px;color:var(--brand)}@media(max-width:650px){.service-work-session-row{grid-template-columns:1fr 1fr 42px}}
</style>
<script data-machinepark-build-fix="service-work-sessions-v1">
(() => {
  const escAttr = (value) => String(value ?? '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const normalizedSessions = (record) => {
    const sessions = Array.isArray(record?.workSessions) ? record.workSessions.filter(row => row && (row.date || Number(row.minutes) > 0)) : [];
    if (sessions.length) return sessions.map(row => ({date:String(row.date||''),minutes:Math.max(0,Math.round(Number(row.minutes)||0))}));
    const legacyMinutes = Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    return legacyMinutes ? [{date:String(record?.date || ''),minutes:legacyMinutes}] : [{date:String(record?.date || ''),minutes:0}];
  };
  const rowHtml = (row={}) => `<div class="service-work-session-row"><input type="date" name="workSessionDate" required value="${escAttr(row.date||'')}" aria-label="Datum werkdag"><input type="number" name="workSessionMinutes" min="1" step="1" required value="${Number(row.minutes)>0?Math.round(Number(row.minutes)):''}" placeholder="minuten" aria-label="Werkduur in minuten"><button type="button" class="remove-line" data-remove-work-session aria-label="Werkdag verwijderen">×</button></div>`;
  const refresh = (root) => {
    if (!root) return;
    const rows = [...root.querySelectorAll('.service-work-session-row')];
    const total = rows.reduce((sum,row)=>sum+Math.max(0,Number(row.querySelector('[name="workSessionMinutes"]')?.value||0)),0);
    const hidden = root.querySelector('[name="hours"]');
    if (hidden) hidden.value = String(total);
    const out = root.querySelector('[data-service-work-total]');
    if (out) out.textContent = `Totaal: ${Math.round(total)} min`;
  };
  window.machineparkServiceWorkSessionsEditor = (record, kind) => {
    const rows = normalizedSessions(record);
    const label = kind === 'breakdown' ? 'depannage' : 'onderhoud';
    return `<div class="field full service-work-sessions" data-service-work-sessions><label>Werkdagen en tijd</label><input name="hours" type="hidden" value="${rows.reduce((s,r)=>s+Number(r.minutes||0),0)}"><div class="service-work-session-list" data-service-work-session-list>${rows.map(rowHtml).join('')}</div><div class="service-work-session-actions"><button type="button" class="btn small" data-add-work-session>+ Dag toevoegen</button><strong data-service-work-total>Totaal: ${rows.reduce((s,r)=>s+Number(r.minutes||0),0)} min</strong></div><div class="muted" style="font-size:11px">De totale tijd geldt voor de volledige ${label}${record?.batchId?'groep':''}.</div></div>`;
  };
  window.machineparkCollectWorkSessions = (fd) => {
    const dates = fd.getAll('workSessionDate');
    const minutes = fd.getAll('workSessionMinutes');
    return dates.map((date,i)=>({date:String(date||''),minutes:Math.max(0,Math.round(Number(minutes[i])||0))})).filter(row=>row.date && row.minutes>0);
  };
  window.machineparkServiceWorkSessionsText = (record) => normalizedSessions(record).filter(row=>row.minutes>0).map(row=>`${row.date || '—'} · ${row.minutes} min`).join(' | ') || '—';
  document.addEventListener('click', (event) => {
    const add = event.target.closest('[data-add-work-session]');
    if (add) {
      const root = add.closest('[data-service-work-sessions]');
      const list = root?.querySelector('[data-service-work-session-list]');
      if (list) { list.insertAdjacentHTML('beforeend', rowHtml({})); list.lastElementChild?.querySelector('input')?.focus(); refresh(root); }
      return;
    }
    const remove = event.target.closest('[data-remove-work-session]');
    if (remove) {
      const root = remove.closest('[data-service-work-sessions]');
      const rows = root?.querySelectorAll('.service-work-session-row');
      if (rows && rows.length > 1) remove.closest('.service-work-session-row')?.remove();
      else { const row=remove.closest('.service-work-session-row'); row?.querySelectorAll('input').forEach(input=>input.value=''); }
      refresh(root);
    }
  });
  document.addEventListener('input', (event) => {
    const root = event.target.closest?.('[data-service-work-sessions]');
    if (root) refresh(root);
  });
})();
</script>
'''
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: body ontbreekt voor meerdaagse werkregistratie')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Werkdagen en tijd',
    'data-add-work-session',
    'workSessionDate',
    'workSessionMinutes',
    'machineparkCollectWorkSessions',
    'workSessions,hours:totalMinutes/60',
    "servicePrintField('Werkdagen'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: meerdaagse servicewerktijd ontbreekt ({needle})')

print('[Machinepark] meerdere werkdagen en automatische totaaltijd voor depannage en onderhoud actief')
