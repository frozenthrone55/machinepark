(() => {
  const AUTOSAVE_DELAY = 1400;
  let activeVisitDraft = null;
  let visitAutosaveTimer = 0;
  let visitSaveChain = Promise.resolve();

  const svEsc = value => esc(String(value ?? ''));
  const svKey = value => normalizeSearch(String(value ?? ''));
  const svDateText = value => {
    if (!value) return '—';
    const d = new Date(`${value}T00:00:00`);
    return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString('nl-BE');
  };
  const svCan = permission => !window.machineparkAccessReady || typeof window.machineparkHasPermission !== 'function' || Boolean(window.machineparkHasPermission(permission));
  const svCanCreate = () => svCan('maintenance.add') || svCan('breakdowns.add');
  const svDeviceShort = deviceId => {
    const d = (state.devices || []).find(item => item.id === deviceId);
    return [d?.assetCode, d?.brand, d?.model].filter(Boolean).join(' · ') || 'Onbekend toestel';
  };
  const svLocationForDevice = device => {
    if (!device) return '';
    try { return deviceLocationAt(device) || device.location || ''; }
    catch (_) { return device.location || ''; }
  };
  const isVisitDraft = item => Boolean(item?.isDraft === true && item?.draftKind === 'serviceVisit');
  const visitDraftHeaders = () => {
    const all = [...(state.maintenance || []), ...(state.breakdowns || [])];
    const seen = new Set();
    return all.filter(item => isVisitDraft(item) && item.draftRole === 'header').filter(item => {
      if (seen.has(item.id)) return false;
      seen.add(item.id);
      return true;
    }).sort((a,b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));
  };
  const visitDraftHeader = id => visitDraftHeaders().find(item => item.id === id) || null;
  const visitDraftItems = id => [...(state.maintenance || []), ...(state.breakdowns || [])]
    .filter(item => isVisitDraft(item) && item.draftRole === 'item' && item.draftBatchId === id);
  const visitDraftStore = header => header?.draftHeaderStore === 'maintenance' ? 'maintenance' : 'breakdowns';

  function serviceVisitRecords(id) {
    const maintenance = (state.maintenance || []).filter(item => item?.isDraft !== true && item?.serviceVisitId === id).map(item => ({ kind:'maintenance', item }));
    const breakdowns = (state.breakdowns || []).filter(item => item?.isDraft !== true && item?.serviceVisitId === id).map(item => ({ kind:'breakdowns', item }));
    return [...maintenance, ...breakdowns].sort((a,b) => String(recordMoment(a.item) || a.item.updatedAt || '').localeCompare(String(recordMoment(b.item) || b.item.updatedAt || '')));
  }

  function serviceVisits() {
    const ids = new Set();
    (state.maintenance || []).forEach(item => { if (item?.isDraft !== true && item?.serviceVisitId) ids.add(item.serviceVisitId); });
    (state.breakdowns || []).forEach(item => { if (item?.isDraft !== true && item?.serviceVisitId) ids.add(item.serviceVisitId); });
    return [...ids].map(id => {
      const records = serviceVisitRecords(id);
      const all = records.map(row => row.item);
      const first = all[0] || {};
      const technicians = [...new Set(all.map(item => String(item.serviceVisitTechnician || item.technician || '').trim()).filter(Boolean))];
      const revisions = all.map(item => Math.max(1, Number(item.serviceVisitRevision) || 1));
      const closed = all.map(item => item.serviceVisitClosedAt || item.updatedAt || '').filter(Boolean).sort();
      return {
        id,
        number:first.serviceVisitNumber || id,
        location:first.serviceVisitLocation || '',
        locationKey:first.serviceVisitLocationKey || svKey(first.serviceVisitLocation || ''),
        date:first.serviceVisitDate || first.date || '',
        time:first.serviceVisitTime || first.time || '',
        technician:technicians.join(', ') || '—',
        revision:Math.max(1, ...revisions),
        closedAt:closed.at(-1) || '',
        records,
        deviceCount:new Set(all.map(item => item.deviceId).filter(Boolean)).size,
        maintenanceCount:records.filter(row => row.kind === 'maintenance').length,
        breakdownCount:records.filter(row => row.kind === 'breakdowns').length,
      };
    }).filter(v => v.records.length).sort((a,b) => String(b.closedAt || `${b.date}T${b.time || '00:00'}`).localeCompare(String(a.closedAt || `${a.date}T${a.time || '00:00'}`)));
  }
  const serviceVisitById = id => serviceVisits().find(v => v.id === id) || null;

  function serviceReports() {
    const rows = [...(state.maintenance || []), ...(state.breakdowns || [])].filter(item => item?.isDraft !== true && item?.serviceVisitId);
    const ids = new Set(rows.map(item => item.serviceReportId || item.serviceVisitId).filter(Boolean));
    return [...ids].map(id => {
      const reportRows = rows.filter(item => (item.serviceReportId || item.serviceVisitId) === id);
      const visitIds = [...new Set(reportRows.map(item => item.serviceVisitId).filter(Boolean))];
      const visits = visitIds.map(visitId => serviceVisitById(visitId)).filter(Boolean);
      const first = reportRows[0] || {};
      const revisions = reportRows.map(item => Math.max(1, Number(item.serviceReportRevision || item.serviceVisitRevision) || 1));
      const closed = reportRows.map(item => item.serviceReportClosedAt || item.serviceVisitClosedAt || item.updatedAt || '').filter(Boolean).sort();
      const technicians = [...new Set(reportRows.map(item => String(item.serviceReportTechnician || item.serviceVisitTechnician || item.technician || '').trim()).filter(Boolean))];
      return {
        id,
        number:first.serviceReportNumber || first.serviceVisitNumber || id,
        revision:Math.max(1,...revisions),
        date:first.serviceReportDate || first.serviceVisitDate || first.date || '',
        time:first.serviceReportTime || first.serviceVisitTime || first.time || '',
        technician:technicians.join(', ') || '—',
        closedAt:closed.at(-1) || '',
        visits:visits.sort((a,b)=>String(a.location||'').localeCompare(String(b.location||''),'nl',{numeric:true,sensitivity:'base'})),
        records:visits.flatMap(v=>v.records),
        locationCount:visits.length,
        deviceCount:new Set(reportRows.map(item=>item.deviceId).filter(Boolean)).size,
        maintenanceCount:reportRows.filter(item=>item.type !== undefined).length,
        breakdownCount:reportRows.filter(item=>item.type === undefined).length,
      };
    }).filter(report=>report.visits.length).sort((a,b)=>String(b.closedAt||`${b.date}T${b.time||'00:00'}`).localeCompare(String(a.closedAt||`${a.date}T${a.time||'00:00'}`)));
  }
  const serviceReportById = id => serviceReports().find(report => report.id === id) || null;
  const serviceReportForVisit = visitId => serviceReports().find(report => report.visits.some(visit => visit.id === visitId)) || null;

  function reportNumber(id,date) {
    const year=String(date||todayISO()).slice(0,4)||String(new Date().getFullYear());
    const suffix=String(id||'').replace(/^sr[_-]?/i,'').replace(/[^a-z0-9]+/gi,'').slice(-8).toUpperCase()||Date.now().toString(36).slice(-8).toUpperCase();
    return `SR-${year}-${suffix}`;
  }

  function svPartLabel(partId) {
    const part = (state.parts || []).find(item => item.id === partId);
    return part ? ([part.artNr, part.description].filter(Boolean).join(' · ') || partId) : `Onbekend onderdeel (${partId || '—'})`;
  }

  function perRecordPartsText(item) {
    const lines = [];
    (item?.usedParts || []).forEach(u => { if (u?.partId && Number(u.qty) > 0) lines.push(`${svPartLabel(u.partId)} × ${Number(u.qty)}`); });
    (item?.oneOffParts || []).forEach(p => {
      const label = [p?.supplier,p?.supplierCode,p?.description].map(v => String(v || '').trim()).filter(Boolean).join(' · ');
      if (label) lines.push(`${label} × ${Math.max(1, Math.round(Number(p.qty) || 1))}`);
    });
    return lines.length ? lines.join('\n') : '—';
  }

  function mergedVisitParts(visit) {
    const merged = new Map();
    for (const row of visit?.records || []) {
      const device = svDeviceShort(row.item.deviceId);
      (row.item.usedParts || []).forEach(u => {
        const qty = Number(u?.qty || 0);
        if (!u?.partId || qty <= 0) return;
        const key = `stock:${u.partId}`;
        if (!merged.has(key)) merged.set(key, { kind:'stock', label:svPartLabel(u.partId), qty:0, devices:new Set() });
        const target = merged.get(key); target.qty += qty; target.devices.add(device);
      });
      (row.item.oneOffParts || []).forEach(p => {
        const label = [p?.supplier,p?.supplierCode,p?.description].map(v => String(v || '').trim()).filter(Boolean).join(' · ');
        if (!label) return;
        const key = `oneoff:${svKey(label)}`;
        if (!merged.has(key)) merged.set(key, { kind:'oneoff', label, qty:0, devices:new Set() });
        const target = merged.get(key); target.qty += Math.max(1, Math.round(Number(p.qty) || 1)); target.devices.add(device);
      });
    }
    return [...merged.values()].map(row => ({...row,devices:[...row.devices].sort((a,b)=>a.localeCompare(b,'nl',{numeric:true,sensitivity:'base'}))}))
      .sort((a,b)=>a.label.localeCompare(b.label,'nl',{numeric:true,sensitivity:'base'}));
  }

  function mergedReportParts(report) {
    const merged=new Map();
    for(const visit of report?.visits||[]) {
      for(const part of mergedVisitParts(visit)) {
        const key=`${part.kind}:${svKey(part.label)}`;
        if(!merged.has(key)) merged.set(key,{kind:part.kind,label:part.label,qty:0,locations:new Set(),devices:new Set()});
        const target=merged.get(key);target.qty+=Number(part.qty||0);target.locations.add(visit.location||'—');(part.devices||[]).forEach(device=>target.devices.add(`${visit.location||'—'} · ${device}`));
      }
    }
    return [...merged.values()].map(row=>({...row,locations:[...row.locations],devices:[...row.devices]})).sort((a,b)=>a.label.localeCompare(b.label,'nl',{numeric:true,sensitivity:'base'}));
  }

  function reportPhotos(report) {
    return (report?.visits||[]).flatMap(visit=>visitPhotos(visit).map(photo=>({...photo,label:`${visit.location||'—'} · ${photo.label}`})));
  }

  function reportWorkSessions(report) {
    const rows=[];
    for(const visit of report?.visits||[]) {
      for(const row of visitWorkSessions(visit)) rows.push({...row,location:visit.location||'—'});
    }
    return rows.sort((a,b)=>a.date.localeCompare(b.date)||String(a.location).localeCompare(String(b.location),'nl'));
  }

  function reportHtml(report) {
    const totalParts=mergedReportParts(report),sessions=reportWorkSessions(report),totalMinutes=sessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);
    return `<div class="service-visit-report service-report">
      <div class="service-visit-report-head"><h3>Serviceverslag ${svEsc(report.number)}</h3><div>${report.locationCount} locatie${report.locationCount===1?'':'s'} · ${report.deviceCount} toestel${report.deviceCount===1?'':'len'}</div></div>
      <div class="service-visit-report-meta">
        <div><small>Datum / uur</small><strong>${svEsc(svDateText(report.date))}${report.time?` · ${svEsc(report.time)}`:''}</strong></div>
        <div><small>Technieker</small><strong>${svEsc(report.technician||'—')}</strong></div>
        <div><small>Status</small><strong>Afgesloten</strong></div>
        <div><small>Versie</small><strong>v${svEsc(report.revision)}</strong></div>
      </div>
      <div><div class="section-title">Werkdagen en tijd</div><div class="service-visit-report-lines">${sessions.length?sessions.map(row=>`<div>${svEsc(svDateText(row.date))} · ${svEsc(row.location)} · <strong>${svEsc(row.minutes)} min</strong></div>`).join(''):'<div>—</div>'}<div><strong>Totaal: ${svEsc(totalMinutes)} min</strong></div></div></div>
      ${(report.visits||[]).map((visit,index)=>`<section class="service-report-location"><div class="service-report-location-head"><span>Locatie ${index+1}</span><h4>${svEsc(visit.location||'—')}</h4></div>${visitReportHtml(visit)}</section>`).join('')}
      <div><div class="section-title">Totaal gebruikte onderdelen · alle locaties</div><table class="service-visit-merged-parts"><thead><tr><th>Onderdeel</th><th>Aantal</th><th>Locaties / toestellen</th></tr></thead><tbody>${totalParts.length?totalParts.map(p=>`<tr><td>${svEsc(p.label)}</td><td><strong>${svEsc(p.qty)}</strong></td><td>${svEsc(p.devices.join(', '))}</td></tr>`).join(''):'<tr><td colspan="3">Geen onderdelen gebruikt.</td></tr>'}</tbody></table></div>
    </div>`;
  }

  function workOrderText(workOrder) {
    if (!workOrder || !Array.isArray(workOrder.fields) || !workOrder.fields.length) return '';
    const rows = workOrder.fields.map(field => {
      const raw = field?.type === 'checkbox' ? (field.value ? 'Ja' : 'Nee') : field?.value;
      return `${field?.label || 'Veld'}: ${raw === '' || raw === null || raw === undefined ? '—' : String(raw)}`;
    });
    return `Werkbon · ${workOrder.templateName || 'Werkbon'} · v${workOrder.templateVersion || 1}\n${rows.join('\n')}`;
  }

  function recordSummary(kind, item, plain = false) {
    const lines = kind === 'maintenance'
      ? [`Type onderhoud: ${item.type || '—'}`, `Uitgevoerde werkzaamheden / notitie: ${item.notes || '—'}`]
      : [`Prioriteit: ${item.priority || '—'} · Status: ${item.status || '—'}`, `Probleem / melding: ${item.issue || '—'}`, `Diagnose: ${item.diagnosis || '—'}`, `Oplossing / uitgevoerde werken: ${item.solution || '—'}`];
    if (item.workOrder) lines.push(workOrderText(item.workOrder));
    if (kind === 'breakdowns' && item.faultRef) lines.push(`Gekoppelde storing: ${[item.faultRef.code,item.faultRef.name].filter(Boolean).join(' — ') || '—'}`);
    lines.push(`Onderdelen op dit toestel: ${perRecordPartsText(item)}`);
    if (plain) return lines.join('\n');
    return `<div class="service-visit-report-record"><h4><span class="badge ${kind === 'maintenance' ? 'blue' : 'danger'}">${kind === 'maintenance' ? 'Onderhoud' : 'Depannage'}</span>${svEsc(svDeviceShort(item.deviceId))}</h4><div class="service-visit-report-lines">${lines.map(line => `<div style="white-space:pre-wrap">${svEsc(line)}</div>`).join('')}</div></div>`;
  }

  function visitPhotos(visit) {
    const out = [];
    for (const row of visit?.records || []) {
      (row.item.photos || []).forEach((src,index) => {
        if (typeof src === 'string' && src.trim()) out.push({ src, label:`${row.kind === 'maintenance' ? 'Onderhoud' : 'Depannage'} · ${svDeviceShort(row.item.deviceId)} · foto ${index + 1}` });
      });
    }
    return out;
  }

  function visitWorkSessions(visit) {
    const seen=new Set(),rows=[];
    for(const record of visit?.records||[]){
      const revision=Math.max(1,Number(record.item?.serviceVisitRevision)||1);
      for(const session of (record.item?.workSessions||[])){
        const date=String(session?.date||''),minutes=Math.max(0,Math.round(Number(session?.minutes)||0));
        if(!date||!minutes)continue;
        const key=`${revision}|${date}|${minutes}`;
        if(seen.has(key))continue;
        seen.add(key);rows.push({revision,date,minutes});
      }
    }
    return rows.sort((a,b)=>a.date.localeCompare(b.date)||a.revision-b.revision);
  }

  function visitReportHtml(visit) {
    const parts = mergedVisitParts(visit);
    const photos = visitPhotos(visit);
    const sessions = visitWorkSessions(visit);
    const totalMinutes = sessions.reduce((sum,row)=>sum+row.minutes,0);
    return `<div class="service-visit-report">
      <div class="service-visit-report-head"><h3>Serviceverslag ${svEsc(visit.number)}</h3><div>${svEsc(visit.location || 'Locatie niet ingevuld')}</div></div>
      <div class="service-visit-report-meta">
        <div><small>Datum / uur</small><strong>${svEsc(svDateText(visit.date))}${visit.time ? ` · ${svEsc(visit.time)}` : ''}</strong></div>
        <div><small>Technieker</small><strong>${svEsc(visit.technician || '—')}</strong></div>
        <div><small>Status</small><strong>Afgesloten</strong></div>
        <div><small>Versie</small><strong>v${svEsc(visit.revision)}</strong></div>
      </div>
      <div><div class="section-title">Werkdagen en tijd</div><div class="service-visit-report-lines">${sessions.length?sessions.map(row=>`<div>${svEsc(svDateText(row.date))} · <strong>${svEsc(row.minutes)} min</strong>${visit.revision>1?` · versie v${svEsc(row.revision)}`:''}</div>`).join(''):'<div>—</div>'}<div><strong>Totaal: ${svEsc(totalMinutes)} min</strong></div></div></div>
      <div><div class="section-title">Werkzaamheden per toestel</div><div style="display:grid;gap:9px">${visit.records.map(row => recordSummary(row.kind,row.item)).join('')}</div></div>
      <div><div class="section-title">Onderdelen · samengevoegd voor klant</div><table class="service-visit-merged-parts"><thead><tr><th>Onderdeel</th><th>Aantal</th><th>Gebruikt op</th></tr></thead><tbody>${parts.length ? parts.map(p => `<tr><td>${svEsc(p.label)}${p.kind === 'oneoff' ? '<div class="muted" style="font-size:10px">Eenmalig / leverancier</div>' : ''}</td><td><strong>${svEsc(p.qty)}</strong></td><td>${svEsc(p.devices.join(', '))}</td></tr>`).join('') : '<tr><td colspan="3">Geen onderdelen gebruikt.</td></tr>'}</tbody></table></div>
      ${photos.length ? `<div><div class="section-title">Foto’s bij servicebezoek</div><div class="service-visit-photo-grid">${photos.map(p => `<figure><img src="${svEsc(p.src)}" data-full-src="${svEsc(p.src)}" data-photo-lightbox alt="${svEsc(p.label)}"><figcaption>${svEsc(p.label)}</figcaption></figure>`).join('')}</div></div>` : ''}
    </div>`;
  }

  function visitNumber(id,date) {
    const year = String(date || todayISO()).slice(0,4) || String(new Date().getFullYear());
    const suffix = String(id || '').replace(/^sv[_-]?/i,'').replace(/[^a-z0-9]+/gi,'').slice(-8).toUpperCase() || Date.now().toString(36).slice(-8).toUpperCase();
    return `SV-${year}-${suffix}`;
  }

  function locationGroups() {
    try { return maintenanceLocationGroups(); }
    catch (_) {
      const map = new Map();
      (state.devices || []).filter(d => (d.status || 'Actief') === 'Actief').forEach(d => {
        const label = svLocationForDevice(d), key = svKey(label);
        if (!label || !key) return;
        if (!map.has(key)) map.set(key,{key,label,devices:[]});
        map.get(key).devices.push(d);
      });
      return [...map.values()];
    }
  }
  function matchLocationGroups(query) {
    const q = svKey(query);
    return locationGroups().filter(group => !q || svKey(group.label).includes(q) || (group.devices || []).some(d => svKey([d.assetCode,d.serial,d.brand,d.model].filter(Boolean).join(' ')).includes(q))).slice(0,12);
  }

  function oneOffRowHtml(p={}) {
    return `<div class="service-visit-oneoff-row"><input class="sv-oneoff-supplier" type="text" maxlength="120" placeholder="Leverancier" value="${svEsc(p.supplier || '')}"><input class="sv-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${svEsc(p.supplierCode || '')}"><input class="sv-oneoff-description" type="text" maxlength="240" placeholder="Omschrijving" value="${svEsc(p.description || '')}"><input class="sv-oneoff-qty" type="number" min="1" step="1" value="${Math.max(1,Math.round(Number(p.qty) || 1))}"><button type="button" class="remove-line sv-remove-oneoff">×</button></div>`;
  }

  function photoDraftHtml(photos=[]) {
    const list = (photos || []).filter(src => typeof src === 'string' && src.trim());
    return list.length ? `<div class="service-photo-grid sv-existing-photos">${list.map((src,i)=>`<div class="service-photo-item"><img src="${svEsc(typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src)}" data-full-src="${svEsc(src)}" data-photo-lightbox alt="Conceptfoto ${i+1}"><label><input type="checkbox" class="sv-remove-photo" value="${i}"> Verwijderen</label></div>`).join('')}</div>` : '';
  }

  function partSection(kind,item={}) {
    const used = (item.usedParts?.length ? item.usedParts : [{partId:'',qty:1}]).map(u => usageRowHtml(u,true)).join('');
    const one = (item.oneOffParts?.length ? item.oneOffParts : [{}]).map(oneOffRowHtml).join('');
    return `<div class="service-visit-parts"><div class="service-visit-parts-head"><strong>Gebruikte onderdelen</strong><button type="button" class="btn small sv-add-part">+ Onderdeelregel</button></div><div class="muted" style="font-size:11px;margin:-3px 0 7px">Onderdelen blijven gekoppeld aan dit toestel en deze ${kind === 'maintenance' ? 'onderhoudsregistratie' : 'depannage'}.</div><div class="usage-list sv-usage-list">${used}</div></div>
      <div class="service-visit-oneoff"><div class="service-visit-parts-head"><strong>Eenmalige onderdelen / leverancier</strong><button type="button" class="btn small sv-add-oneoff">+ Eenmalig onderdeel</button></div><div class="service-visit-oneoff-list">${one}</div></div>
      <div class="field full sv-photo-editor" data-existing-photos='${svEsc(JSON.stringify(item.photos || []))}'><label>Foto’s bij ${kind === 'maintenance' ? 'onderhoud' : 'depannage'}</label>${photoDraftHtml(item.photos || [])}<input class="sv-photo-files" type="file" accept="image/*" multiple><div class="muted" style="font-size:11px;margin-top:4px">Maximaal 5 foto’s per toestelregistratie.</div></div>`;
  }

  function existingKinds(visit) {
    const map = new Map();
    for (const row of visit?.records || []) {
      if (!map.has(row.item.deviceId)) map.set(row.item.deviceId,new Set());
      map.get(row.item.deviceId).add(row.kind);
    }
    return map;
  }

  function itemMap(items=[]) {
    return new Map(items.map(item => [`${item.draftServiceKind || (item.issue !== undefined ? 'breakdowns' : 'maintenance')}:${item.deviceId}`,item]));
  }

  function deviceCard(device,visit=null,draftItems=[]) {
    const existing = existingKinds(visit).get(device.id) || new Set();
    const drafts = itemMap(draftItems);
    const m = drafts.get(`maintenance:${device.id}`) || {};
    const b = drafts.get(`breakdowns:${device.id}`) || {};
    const mChecked = Boolean(m.id), bChecked = Boolean(b.id);
    const editing=Boolean(activeVisitDraft?.editMode);
    const canM = svCan('maintenance.add') && (editing || !existing.has('maintenance'));
    const canB = svCan('breakdowns.add') && (editing || !existing.has('breakdowns'));
    const machine = [device.brand,device.model].filter(Boolean).join(' ') || 'Geen toestelomschrijving';
    const loc = svLocationForDevice(device);
    return `<div class="service-visit-device breakdown-machine-card" data-service-visit-device="${svEsc(device.id)}" data-breakdown-device="${svEsc(device.id)}">
      <div class="service-visit-device-head"><div><strong>${svEsc(device.assetCode || device.model || 'Toestel')}</strong><small>${svEsc(machine)}${device.serial ? ` · S/N ${svEsc(device.serial)}` : ''}${loc ? ` · ${svEsc(loc)}` : ''}</small><div class="sv-manual-panel manual-inline-panel"></div></div>
        <div class="service-visit-kind-picks"><button type="button" class="btn small sv-manual-btn" data-sv-manuals="${svEsc(device.id)}">📘 Handleidingen</button><label class="${canM ? '' : 'disabled'}"><input type="checkbox" data-kind="maintenance" ${mChecked ? 'checked' : ''} ${canM ? '' : 'disabled'} ${editing&&existing.has('maintenance')?'data-existing-kind="1"':''}> Onderhoud${existing.has('maintenance') ? (editing?' · bewerken':' · al in verslag') : ''}</label><label class="${canB ? '' : 'disabled'}"><input type="checkbox" class="breakdown-machine-check" data-kind="breakdowns" ${bChecked ? 'checked' : ''} ${canB ? '' : 'disabled'} ${editing&&existing.has('breakdowns')?'data-existing-kind="1"':''}> Depannage${existing.has('breakdowns') ? (editing?' · bewerken':' · al in verslag') : ''}</label></div></div>
      <div class="service-visit-kind-panel ${mChecked ? 'active' : ''}" data-panel-kind="maintenance"><h4>Onderhoud · ${svEsc(device.assetCode || device.model || 'Toestel')}</h4><div class="service-visit-grid"><div><label>Type onderhoud *</label><select class="sv-maintenance-type">${['Halfjaarlijks','Jaarlijks','Op afroep','Maandelijks'].map(v=>`<option ${m.type===v?'selected':''}>${v}</option>`).join('')}</select></div><div class="full"><label>Uitgevoerde werkzaamheden / notitie</label><textarea class="sv-maintenance-notes">${svEsc(m.notes || '')}</textarea></div>${partSection('maintenance',m)}</div></div>
      <div class="service-visit-kind-panel ${bChecked ? 'active' : ''}" data-panel-kind="breakdowns"><h4>Depannage · ${svEsc(device.assetCode || device.model || 'Toestel')}</h4><div class="service-visit-grid"><div><label>Prioriteit</label><select class="sv-breakdown-priority">${['Laag','Normaal','Hoog','Kritiek'].map(v=>`<option ${String(b.priority || 'Normaal')===v?'selected':''}>${v}</option>`).join('')}</select></div><div><label>Status</label><select class="sv-breakdown-status">${['Open','In behandeling','Opgelost'].map(v=>`<option ${String(b.status || 'Open')===v?'selected':''}>${v}</option>`).join('')}</select></div><div class="full"><label>Probleem / melding *</label><textarea class="sv-breakdown-issue breakdown-machine-issue">${svEsc(b.issue || '')}</textarea></div><div class="full"><label>Diagnose</label><textarea class="sv-breakdown-diagnosis">${svEsc(b.diagnosis || '')}</textarea></div><div class="full"><label>Oplossing / uitgevoerde werken</label><textarea class="sv-breakdown-solution breakdown-machine-solution">${svEsc(b.solution || '')}</textarea></div>${partSection('breakdowns',b)}</div></div>
    </div>`;
  }

  function reportEditHeader(report) {
    if(!report)return null;
    const locations=(report.visits||[]).map(visit=>({key:visit.locationKey||svKey(visit.location),label:visit.location||'—',visitId:visit.id}));
    const locationSessions={};
    for(const visit of report.visits||[]) {
      const key=visit.locationKey||svKey(visit.location);
      const first=visit.records?.[0]?.item;
      locationSessions[key]=Array.isArray(first?.workSessions)?first.workSessions.map(row=>({date:String(row.date||''),minutes:Math.max(0,Math.round(Number(row.minutes)||0))})).filter(row=>row.date&&row.minutes>0):[];
    }
    return {locations,activeLocationKey:locations[0]?.key||'',date:report.date||todayISO(),time:report.time||nowLocalTime(),technician:report.technician==='—'?'':report.technician||'',locationSessions,appendToReportId:report.id,editReportId:report.id};
  }

  function reportEditItems(report,draftBatchId) {
    const now=new Date().toISOString(),out=[];
    for(const visit of report?.visits||[]) {
      const locationKey=visit.locationKey||svKey(visit.location),locationLabel=visit.location||'';
      for(const row of visit.records||[]) {
        const src=row.item||{},kind=row.kind;
        out.push({...src,
          id:uid(kind==='maintenance'?'mntdraft':'brkdraft'),
          sourceRecordId:src.id,
          sourceUsedParts:Array.isArray(src.usedParts)?src.usedParts.map(p=>({...p})):[],
          isDraft:true,draftRole:'item',draftKind:'serviceVisit',draftBatchId,
          draftServiceKind:kind,draftLocationKey:locationKey,draftLocationLabel:locationLabel,
          targetVisitId:visit.id,createdAt:now,updatedAt:now,draftSchema:3
        });
      }
    }
    return out;
  }

  function draftLocationList(report=null,header=null) {
    const fromReport=(report?.visits||[]).map(visit=>({key:visit.locationKey||svKey(visit.location),label:visit.location||'—',visitId:visit.id}));
    const fromHeader=Array.isArray(header?.locations)?header.locations.map(loc=>({key:String(loc?.key||''),label:String(loc?.label||''),visitId:String(loc?.visitId||'')})).filter(loc=>loc.key&&loc.label):[];
    if(fromHeader.length)return fromHeader;
    if(fromReport.length)return fromReport;
    if(header?.locationKey&&header?.locationLabel)return[{key:header.locationKey,label:header.locationLabel,visitId:header.appendToVisitId||''}];
    return[];
  }

  function serviceVisitForm({report=null,visit=null,header=null,items=[]}={}) {
    const locations=draftLocationList(report,header);
    const activeKey=header?.activeLocationKey||locations[0]?.key||visit?.locationKey||'';
    const active=locations.find(loc=>loc.key===activeKey)||locations[0]||null;
    const location=active?.label||visit?.location||header?.locationLabel||'';
    const locationKey=active?.key||visit?.locationKey||header?.locationKey||'';
    const date=report?.date||visit?.date||header?.date||todayISO();
    const time=report?.time||visit?.time||header?.time||nowLocalTime();
    const technician=header?.technician??(report?.technician==='—'?'':report?.technician||visit?.technician==='—'?'':visit?.technician||'');
    const headerLocationSessions=header?.locationSessions?.[locationKey];
    const existingVisitSessions=visit?.records?.[0]?.item?.workSessions||[];
    const sessionSource={date,workSessions:Array.isArray(headerLocationSessions)?headerLocationSessions:(Array.isArray(existingVisitSessions)?existingVisitSessions:[])};
    const workSessionsHtml=typeof window.machineparkServiceWorkSessionsEditor==='function'
      ?window.machineparkServiceWorkSessionsEditor(sessionSource,'servicevisit')
      :`<div class="field full"><label>Werkdagen en tijd</label><input name="workSessionDate" type="date" required value="${svEsc(date)}"><input name="workSessionMinutes" type="number" min="1" step="1" required placeholder="minuten"></div>`;
    const chips=locations.map(loc=>`<button type="button" class="service-report-location-chip ${loc.key===locationKey?'active':''}" data-sv-location-switch="${svEsc(loc.key)}"><span>${svEsc(loc.label)}</span>${loc.visitId?'<small>Bestaande locatie</small>':'<small>Concept</small>'}</button>`).join('');
    return `<div class="form-grid"><div class="service-visit-form-note"><strong>Eén serviceverslag, meerdere locaties.</strong> Elke locatie behoudt intern haar eigen servicebezoek. Onderhoud en depannage blijven aparte records per toestel; onderdelen blijven per toestel gekoppeld en worden in het klantverslag per locatie én totaal samengevoegd.</div>
      ${report?`<div class="service-visit-existing"><strong>Aanvulling op ${svEsc(report.number)} · huidige versie v${svEsc(report.revision)}</strong><div class="muted" style="font-size:11px;margin-top:3px">Je kunt een toestel aan een bestaande locatie toevoegen of een volledig nieuwe locatie aan hetzelfde verslag toevoegen.</div></div>`:''}
      <div class="field full service-report-location-manager"><div class="service-report-location-manager-head"><div><label>Locaties in dit verslag *</label><div class="muted" style="font-size:11px">Wissel tussen locaties om de toestellen en werkzaamheden in te vullen.</div></div><button type="button" class="btn small primary" id="serviceReportAddLocation">+ Locatie toevoegen</button></div><div id="serviceReportLocationChips" class="service-report-location-chips">${chips||'<span class="muted">Nog geen locatie gekozen.</span>'}</div></div>
      <div class="field full" id="serviceReportLocationPicker"><label>${locations.length?'Actieve locatie':'Eerste locatie'} *</label><div class="maintenance-location-autocomplete"><input id="serviceVisitLocationSearch" type="search" autocomplete="off" placeholder="Typ locatie of toestelnummer…" value="${svEsc(location)}"><input id="serviceVisitLocationKey" name="locationKey" type="hidden" value="${svEsc(locationKey)}"><div id="serviceVisitLocationSuggestions" class="maintenance-location-suggestions"></div></div><div id="serviceVisitLocationCount" class="muted" style="font-size:11px;margin-top:4px">${location?`Locatie: ${svEsc(location)}`:'Typ een locatie of toestelnummer en kies de locatie uit de lijst.'}</div></div>
      <div class="field"><label>Datum *</label><input name="date" type="date" required value="${svEsc(date)}"></div><div class="field"><label>Uur *</label><input name="time" type="time" required value="${svEsc(time)}"></div>
      <div class="field"><label>Technieker</label><input name="technician" value="${svEsc(technician)}"></div><div id="serviceReportLocationSessions" class="field full"><div class="section-title">Werktijd op actieve locatie</div>${workSessionsHtml}</div>
      <div class="field full"><div class="section-title">Toestellen op actieve locatie</div><div class="muted" style="font-size:11px">Kies per toestel Onderhoud, Depannage of beide. Handleidingen, werkbonnen, storingen, foto's en onderdelen blijven aan dit toestel gekoppeld.</div></div>
      <div id="serviceVisitDevices" class="service-visit-device-list"><div class="empty" style="padding:24px">${location?'Toestellen laden…':'Kies eerst een locatie.'}</div></div></div>`;
  }

  async function showManuals(button) {
    const deviceId = button.dataset.svManuals || '';
    const card = button.closest('.service-visit-device');
    const panel = card?.querySelector('.sv-manual-panel');
    if (!panel) return;
    button.disabled = true;
    try {
      if (typeof window.machineparkManualListHtml !== 'function') {
        panel.innerHTML = '<div class="muted" style="font-size:11px">Handleidingenmodule is niet beschikbaar.</div>';
      } else {
        panel.innerHTML = await window.machineparkManualListHtml(deviceId,true);
        panel.classList.add('show');
      }
    } catch (error) {
      panel.innerHTML = `<div class="muted" style="font-size:11px">${svEsc(error?.message || 'Handleidingen konden niet worden geladen.')}</div>`;
      panel.classList.add('show');
    } finally { button.disabled = false; }
  }

  function bindVisitInteractions(root) {
    if (!root || root.dataset.svBound === '1') return;
    root.dataset.svBound = '1';
    const closeSuggestions = row => row?.querySelector('.usage-suggestions')?.classList.remove('show');
    root.addEventListener('click',event => {
      const manuals = event.target.closest('[data-sv-manuals]'); if (manuals) { void showManuals(manuals); return; }
      const addPart = event.target.closest('.sv-add-part'); if (addPart) { const list=addPart.closest('.service-visit-parts')?.querySelector('.sv-usage-list'); if(list){const h=document.createElement('div');h.innerHTML=usageRowHtml({partId:'',qty:1},true);if(h.firstElementChild)list.appendChild(h.firstElementChild);list.lastElementChild?.querySelector('.usage-search')?.focus();} return; }
      const suggestion=event.target.closest('.usage-suggestion'); if(suggestion?.closest('.sv-usage-list')){const row=suggestion.closest('.usage-row'),part=(state.parts||[]).find(p=>p.id===suggestion.dataset.partId),search=row?.querySelector('.usage-search'),hidden=row?.querySelector('.usage-part');if(part&&search&&hidden){search.value=usagePartDisplay(part);hidden.value=part.id;closeSuggestions(row);}return;}
      const remove=event.target.closest('.sv-usage-list .remove-line'); if(remove){const list=remove.closest('.sv-usage-list'),rows=list?.querySelectorAll('.usage-row')||[];if(rows.length>1)remove.closest('.usage-row')?.remove();else{const row=remove.closest('.usage-row');if(row?.querySelector('.usage-search'))row.querySelector('.usage-search').value='';if(row?.querySelector('.usage-part'))row.querySelector('.usage-part').value='';if(row?.querySelector('.usage-qty'))row.querySelector('.usage-qty').value='1';}return;}
      const addOne=event.target.closest('.sv-add-oneoff');if(addOne){const list=addOne.closest('.service-visit-oneoff')?.querySelector('.service-visit-oneoff-list');if(list){list.insertAdjacentHTML('beforeend',oneOffRowHtml());list.lastElementChild?.querySelector('.sv-oneoff-supplier')?.focus();}return;}
      const removeOne=event.target.closest('.sv-remove-oneoff');if(removeOne){const list=removeOne.closest('.service-visit-oneoff-list'),rows=list?.querySelectorAll('.service-visit-oneoff-row')||[];if(rows.length>1)removeOne.closest('.service-visit-oneoff-row')?.remove();else removeOne.closest('.service-visit-oneoff-row')?.querySelectorAll('input').forEach(i=>i.value=i.type==='number'?'1':'');}
    });
    root.addEventListener('change',event=>{const toggle=event.target.closest('[data-kind]');if(toggle){const panel=toggle.closest('.service-visit-device')?.querySelector(`[data-panel-kind="${toggle.dataset.kind}"]`);panel?.classList.toggle('active',toggle.checked);panel?.querySelectorAll('[data-workorder-editor] input,[data-workorder-editor] select,[data-workorder-editor] textarea').forEach(el=>{el.disabled=!toggle.checked;});}});
    root.addEventListener('input',event=>{const input=event.target.closest('.sv-usage-list .usage-search');if(!input)return;const row=input.closest('.usage-row'),menu=row?.querySelector('.usage-suggestions'),hidden=row?.querySelector('.usage-part');if(hidden)hidden.value='';const q=input.value.trim();if(!menu)return;if(!q){menu.innerHTML='';menu.classList.remove('show');return;}menu.innerHTML=usageSuggestionsHtml(q);menu.classList.add('show');});
    root.addEventListener('keydown',event=>{const input=event.target.closest('.sv-usage-list .usage-search');if(!input)return;const menu=input.closest('.usage-row')?.querySelector('.usage-suggestions');if(event.key==='Escape')menu?.classList.remove('show');if(event.key==='Enter'&&menu?.classList.contains('show')){const first=menu.querySelector('.usage-suggestion');if(first){event.preventDefault();first.click();}}});
    root.addEventListener('focusout',event=>{const input=event.target.closest('.sv-usage-list .usage-search');if(input)setTimeout(()=>closeSuggestions(input.closest('.usage-row')),140);});
  }

  function findGroup(locationKey,locationLabel='') {
    return locationGroups().find(g=>g.key===locationKey) || locationGroups().find(g=>svKey(g.label)===svKey(locationLabel)) || null;
  }

  function renderDevices(group,visit=null,draftItems=[]) {
    const box=document.getElementById('serviceVisitDevices'),count=document.getElementById('serviceVisitLocationCount');if(!box)return;
    if(!group){box.innerHTML='<div class="empty" style="padding:24px">Geen actieve toestellen op deze locatie gevonden.</div>';return;}
    box.innerHTML=(group.devices||[]).map(d=>deviceCard(d,visit,draftItems)).join('')||'<div class="empty" style="padding:24px">Geen actieve toestellen op deze locatie gevonden.</div>';
    if(count)count.textContent=`${group.devices?.length||0} actief toestel${group.devices?.length===1?'':'len'} op ${group.label}`;
    bindVisitInteractions(box);
    void attachVisitExtras(draftItems);
  }

  async function attachVisitExtras(draftItems=[]) {
    const drafts=itemMap(draftItems);
    if(typeof window.machineparkLoadWorkOrderTemplates==='function'){try{await window.machineparkLoadWorkOrderTemplates();}catch(_){}}
    document.querySelectorAll('#serviceVisitDevices .service-visit-device').forEach(card=>{
      const deviceId=card.dataset.serviceVisitDevice||'',device=(state.devices||[]).find(d=>d.id===deviceId)||{};
      for(const kind of ['maintenance','breakdowns']){
        const panel=card.querySelector(`[data-panel-kind="${kind}"]`);
        if(!panel||panel.querySelector('[data-workorder-editor]')||typeof window.machineparkMakeWorkOrderEditor!=='function')continue;
        const saved=drafts.get(`${kind}:${deviceId}`)?.workOrder||null;
        const editor=window.machineparkMakeWorkOrderEditor(device,saved);
        panel.querySelector('.service-visit-grid')?.appendChild(editor);
        const enabled=Boolean(card.querySelector(`[data-kind="${kind}"]`)?.checked);
        editor.querySelectorAll('input,select,textarea').forEach(el=>{el.disabled=!enabled;});
      }
    });
    if(typeof window.machineparkAugmentBreakdownFaultCards==='function')window.machineparkAugmentBreakdownFaultCards();
    document.querySelectorAll('#serviceVisitDevices .service-visit-device').forEach(card=>{
      const saved=drafts.get(`breakdowns:${card.dataset.serviceVisitDevice||''}`)?.faultRef;
      const holder=card.querySelector('.fault-inline-tools');
      if(saved&&holder){holder._machineparkFaultSnapshot=saved;const selected=holder.querySelector('.fault-picker-selected');if(selected)selected.textContent=`Gekoppeld: ${[saved.code,saved.name].filter(Boolean).join(' — ')}`;}
    });
  }

  function locationItems(items,key,fallbackKey='') {
    return (items||[]).filter(item => String(item.draftLocationKey || fallbackKey || '') === String(key||''));
  }

  function visitForLocation(report,key) {
    return (report?.visits||[]).find(visit => String(visit.locationKey||svKey(visit.location)) === String(key||'')) || null;
  }

  function existingReportLocationSessions(report,key) {
    const visit=visitForLocation(report,key);
    const first=visit?.records?.[0]?.item;
    return Array.isArray(first?.workSessions)?first.workSessions.map(row=>({date:String(row.date||''),minutes:Math.max(0,Math.round(Number(row.minutes)||0))})).filter(row=>row.date&&row.minutes>0):[];
  }

  function captureActiveLocationSessions() {
    if(!activeVisitDraft?.activeLocationKey)return;
    const form=document.getElementById('modalForm');if(!form)return;
    const fd=new FormData(form);
    const rows=typeof window.machineparkCollectWorkSessions==='function'
      ?window.machineparkCollectWorkSessions(fd)
      :[];
    activeVisitDraft.locationSessions=activeVisitDraft.locationSessions||{};
    activeVisitDraft.locationSessions[activeVisitDraft.activeLocationKey]=rows;
  }

  function renderActiveLocationSessions(key) {
    const host=document.getElementById('serviceReportLocationSessions');if(!host||!activeVisitDraft)return;
    const date=String(document.getElementById('modalForm')?.elements.date?.value||todayISO());
    const rows=activeVisitDraft.locationSessions?.[key]||existingReportLocationSessions(activeVisitDraft.report,key);
    const source={date,workSessions:Array.isArray(rows)?rows:[]};
    const editor=typeof window.machineparkServiceWorkSessionsEditor==='function'
      ?window.machineparkServiceWorkSessionsEditor(source,'servicevisit')
      :`<div class="field full"><label>Werkdagen en tijd</label><input name="workSessionDate" type="date" required value="${svEsc(date)}"><input name="workSessionMinutes" type="number" min="1" step="1" required placeholder="minuten"></div>`;
    host.innerHTML=`<div class="section-title">Werktijd op ${svEsc((activeVisitDraft.locations||[]).find(loc=>loc.key===key)?.label||'actieve locatie')}</div>${editor}`;
  }

  function renderLocationChips() {
    const box=document.getElementById('serviceReportLocationChips');if(!box||!activeVisitDraft)return;
    box.innerHTML=(activeVisitDraft.locations||[]).length
      ?activeVisitDraft.locations.map(loc=>`<span class="service-report-location-chip-wrap"><button type="button" class="service-report-location-chip ${loc.key===activeVisitDraft.activeLocationKey?'active':''}" data-sv-location-switch="${svEsc(loc.key)}"><span>${svEsc(loc.label)}</span>${loc.visitId?'<small>Bestaande locatie</small>':'<small>Concept</small>'}</button>${loc.visitId?'':`<button type="button" class="service-report-location-remove" data-sv-location-remove="${svEsc(loc.key)}" title="Locatie verwijderen">×</button>`}</span>`).join('')
      :'<span class="muted">Nog geen locatie gekozen.</span>';
  }

  async function switchDraftLocation(group,{capture=true}={}) {
    if(!activeVisitDraft||!group)return;
    if(capture&&activeVisitDraft.activeLocationKey&&activeVisitDraft.activeLocationKey!==group.key) {
      captureActiveLocationSessions();
      activeVisitDraft.items=await collectItems();
    }
    let loc=(activeVisitDraft.locations||[]).find(item=>item.key===group.key);
    if(!loc){loc={key:group.key,label:group.label,visitId:''};activeVisitDraft.locations.push(loc);}
    activeVisitDraft.activeLocationKey=group.key;
    const input=document.getElementById('serviceVisitLocationSearch'),hidden=document.getElementById('serviceVisitLocationKey');
    if(input){input.value=group.label;input.setCustomValidity('');}
    if(hidden)hidden.value=group.key;
    renderLocationChips();
    renderActiveLocationSessions(group.key);
    const report=activeVisitDraft.report||null,existingVisit=visitForLocation(report,group.key);
    const items=locationItems(activeVisitDraft.items,group.key,activeVisitDraft.header?.locationKey||'');
    renderDevices(group,existingVisit,items);
    activeVisitDraft.touched=true;scheduleDraft();
  }

  function initVisitForm({report=null,visit=null,header=null,items=[]}={}) {
    const input=document.getElementById('serviceVisitLocationSearch'),hidden=document.getElementById('serviceVisitLocationKey'),suggestions=document.getElementById('serviceVisitLocationSuggestions'),form=document.getElementById('modalForm'),add=document.getElementById('serviceReportAddLocation');if(!input||!hidden||!suggestions||!form||!activeVisitDraft)return;
    const initialLocations=draftLocationList(report,header);
    activeVisitDraft.locations=(activeVisitDraft.locations?.length?activeVisitDraft.locations:initialLocations).map(loc=>({...loc}));
    activeVisitDraft.activeLocationKey=activeVisitDraft.activeLocationKey||header?.activeLocationKey||activeVisitDraft.locations[0]?.key||hidden.value||'';
    renderLocationChips();
    const initial=activeVisitDraft.locations.find(loc=>loc.key===activeVisitDraft.activeLocationKey);
    if(initial){const group=findGroup(initial.key,initial.label);if(group)void switchDraftLocation(group,{capture:false});}
    else renderDevices(null);

    const hide=()=>suggestions.classList.remove('show');
    const render=()=>{const matches=matchLocationGroups(input.value).filter(g=>!(activeVisitDraft.locations||[]).some(loc=>loc.key===g.key)||g.key===activeVisitDraft.activeLocationKey);suggestions.innerHTML=matches.length?matches.map(g=>`<button type="button" class="maintenance-location-suggestion" data-sv-location="${svEsc(g.key)}"><strong>${svEsc(g.label)}</strong><small>${g.devices.length} actief toestel${g.devices.length===1?'':'len'}</small></button>`).join(''):'<div class="maintenance-location-empty">Geen andere locatie of toestelnummer gevonden.</div>';suggestions.classList.add('show');};
    input.addEventListener('focus',render);
    input.addEventListener('input',()=>{hidden.value='';render();});
    input.addEventListener('keydown',e=>{if(e.key==='Escape')hide();if(e.key==='Enter'&&suggestions.classList.contains('show')){const first=suggestions.querySelector('[data-sv-location]');if(first){e.preventDefault();first.click();}}});
    suggestions.addEventListener('click',e=>{const choice=e.target.closest('[data-sv-location]');if(!choice)return;const group=locationGroups().find(g=>g.key===choice.dataset.svLocation);if(!group)return;hide();void switchDraftLocation(group);});
    document.getElementById('serviceReportLocationChips')?.addEventListener('click',e=>{
      const remove=e.target.closest('[data-sv-location-remove]');
      if(remove){const key=remove.dataset.svLocationRemove||'',loc=(activeVisitDraft.locations||[]).find(x=>x.key===key);if(!loc||loc.visitId)return;if(!confirm(`Locatie ${loc.label} uit dit concept verwijderen? De reeds afgesloten locaties worden niet geraakt.`))return;activeVisitDraft.items=(activeVisitDraft.items||[]).filter(item=>String(item.draftLocationKey||'')!==key);delete activeVisitDraft.locationSessions?.[key];activeVisitDraft.locations=activeVisitDraft.locations.filter(x=>x.key!==key);if(activeVisitDraft.activeLocationKey===key){activeVisitDraft.activeLocationKey=activeVisitDraft.locations[0]?.key||'';const next=activeVisitDraft.locations[0],group=next?findGroup(next.key,next.label):null;if(group)void switchDraftLocation(group,{capture:false});else renderDevices(null);}renderLocationChips();scheduleDraft();return;}
      const chip=e.target.closest('[data-sv-location-switch]');if(!chip)return;const loc=(activeVisitDraft.locations||[]).find(x=>x.key===chip.dataset.svLocationSwitch);const group=loc?findGroup(loc.key,loc.label):null;if(group)void switchDraftLocation(group);
    });
    if(add)add.onclick=async()=>{if(activeVisitDraft.activeLocationKey){captureActiveLocationSessions();activeVisitDraft.items=await collectItems();}activeVisitDraft.activeLocationKey='';hidden.value='';input.value='';renderLocationChips();renderDevices(null);input.focus();render();scheduleDraft();};
  }

  function collectUsed(panel){return [...(panel?.querySelectorAll('.sv-usage-list .usage-row')||[])].map(r=>({partId:r.querySelector('.usage-part')?.value||'',qty:Number(r.querySelector('.usage-qty')?.value||1)})).filter(u=>u.partId&&u.qty>0);}
  function collectOneOff(panel){return [...(panel?.querySelectorAll('.service-visit-oneoff-row')||[])].map(r=>({supplier:String(r.querySelector('.sv-oneoff-supplier')?.value||'').trim(),supplierCode:String(r.querySelector('.sv-oneoff-code')?.value||'').trim(),description:String(r.querySelector('.sv-oneoff-description')?.value||'').trim(),qty:Math.max(1,Math.round(Number(r.querySelector('.sv-oneoff-qty')?.value)||1))})).filter(p=>p.supplier||p.supplierCode||p.description);}
  function existingPhotoList(panel){const editor=panel?.querySelector('.sv-photo-editor');if(!editor)return[];try{return JSON.parse(editor.dataset.existingPhotos||'[]').filter(v=>typeof v==='string'&&v.trim());}catch(_){return[];}}

  async function collectPhotos(panel,kind,recordId,old=[]) {
    const editor=panel?.querySelector('.sv-photo-editor');
    if(!editor)return old||[];
    const current=existingPhotoList(panel).length?existingPhotoList(panel):(old||[]);
    const remove=new Set([...editor.querySelectorAll('.sv-remove-photo:checked')].map(x=>Number(x.value)));
    const kept=current.filter((_,i)=>!remove.has(i));
    const files=[...(editor.querySelector('.sv-photo-files')?.files||[])].filter(f=>f&&f.size);
    if(kept.length+files.length>5)throw new Error(`Maximaal 5 foto’s per toestelregistratie (${svDeviceShort(panel.closest('.service-visit-device')?.dataset.serviceVisitDevice)}).`);
    const added=[];for(const file of files)added.push(await compressImage(file));
    const merged=[...kept,...added].filter(Boolean);
    const store=kind==='maintenance'?'maintenance':'breakdowns';
    if(typeof window.machineparkPersistServicePhotos==='function')return await window.machineparkPersistServicePhotos(store,recordId,merged);
    return merged;
  }

  function collectHeader() {
    const form=document.getElementById('modalForm'),existing=activeVisitDraft?.header||null,now=new Date().toISOString();
    const active=(activeVisitDraft?.locations||[]).find(loc=>loc.key===activeVisitDraft?.activeLocationKey)||null;
    const fd=new FormData(form);
    captureActiveLocationSessions();
    const workSessions=activeVisitDraft.locationSessions?.[activeVisitDraft.activeLocationKey]||[];
    const locationSessions={...(activeVisitDraft.locationSessions||{})};
    const locations=(activeVisitDraft?.locations||[]).map(loc=>({key:String(loc.key||''),label:String(loc.label||''),visitId:String(loc.visitId||'')})).filter(loc=>loc.key&&loc.label);
    return {...(existing||{}),id:activeVisitDraft.id,isDraft:true,draftRole:'header',draftKind:'serviceVisit',draftBatchId:activeVisitDraft.id,draftHeaderStore:activeVisitDraft.headerStore,locationKey:active?.key||'',locationLabel:active?.label||'',locations,activeLocationKey:active?.key||'',date:String(form?.elements.date?.value||''),time:String(form?.elements.time?.value||''),technician:String(form?.elements.technician?.value||'').trim(),workSessions,locationSessions,appendToVisitId:activeVisitDraft.appendToVisitId||'',appendToReportId:activeVisitDraft.appendToReportId||'',createdAt:existing?.createdAt||activeVisitDraft.createdAt||now,updatedAt:now,draftSchema:2};
  }

  async function collectItems() {
    const activeKey=activeVisitDraft?.activeLocationKey||String(document.getElementById('serviceVisitLocationKey')?.value||'');
    const activeLoc=(activeVisitDraft?.locations||[]).find(loc=>loc.key===activeKey)||null;
    const legacyKey=activeVisitDraft?.header?.locationKey||'';
    const oldItems=activeVisitDraft?.items||[];
    if(!activeKey)return oldItems;
    const preserved=oldItems.filter(item=>String(item.draftLocationKey||legacyKey||'')!==String(activeKey));
    const oldMap=new Map(oldItems.filter(item=>String(item.draftLocationKey||legacyKey||'')===String(activeKey)).map(i=>[`${i.draftServiceKind}:${i.deviceId}`,i]));
    const out=[],now=new Date().toISOString();
    for(const card of document.querySelectorAll('#serviceVisitDevices .service-visit-device')){
      const deviceId=card.dataset.serviceVisitDevice||'';
      for(const kind of ['maintenance','breakdowns']){
        const checked=card.querySelector(`[data-kind="${kind}"]`)?.checked;
        if(!checked)continue;
        const panel=card.querySelector(`[data-panel-kind="${kind}"]`),old=oldMap.get(`${kind}:${deviceId}`)||null,id=old?.id||uid(kind==='maintenance'?'mntdraft':'brkdraft');
        const photos=await collectPhotos(panel,kind,id,old?.photos||[]);
        const editor=panel?.querySelector('[data-workorder-editor]');
        const workOrder=editor&&typeof window.machineparkCollectWorkOrder==='function'?window.machineparkCollectWorkOrder(editor):old?.workOrder||null;
        const base={...(old||{}),id,isDraft:true,draftRole:'item',draftKind:'serviceVisit',draftBatchId:activeVisitDraft.id,draftServiceKind:kind,draftLocationKey:activeKey,draftLocationLabel:activeLoc?.label||'',targetVisitId:activeLoc?.visitId||old?.targetVisitId||'',deviceId,usedParts:collectUsed(panel),oneOffParts:collectOneOff(panel),photos,workOrder,createdAt:old?.createdAt||now,updatedAt:now,draftSchema:2};
        if(kind==='maintenance')out.push({...base,type:panel?.querySelector('.sv-maintenance-type')?.value||'Halfjaarlijks',notes:panel?.querySelector('.sv-maintenance-notes')?.value.trim()||''});
        else out.push({...base,priority:panel?.querySelector('.sv-breakdown-priority')?.value||'Normaal',status:panel?.querySelector('.sv-breakdown-status')?.value||'Open',issue:panel?.querySelector('.sv-breakdown-issue')?.value.trim()||'',diagnosis:panel?.querySelector('.sv-breakdown-diagnosis')?.value.trim()||'',solution:panel?.querySelector('.sv-breakdown-solution')?.value.trim()||'',faultRef:typeof window.machineparkFaultRefFromCard==='function'?window.machineparkFaultRefFromCard(card):old?.faultRef||null});
      }
    }
    return [...preserved,...out];
  }

  function writeDraft(header,items) {
    const previous=[...(activeVisitDraft?.items||[]),...(activeVisitDraft?.header?[activeVisitDraft.header]:[])];
    return new Promise((resolve,reject)=>{
      let tr;try{tr=db.transaction(['maintenance','breakdowns'],'readwrite');}catch(e){reject(e);return;}
      const ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns');
      previous.forEach(item=>(item.draftServiceKind==='maintenance'||item.draftHeaderStore==='maintenance'?ms:bs).delete(item.id));
      (header.draftHeaderStore==='maintenance'?ms:bs).put(header);
      items.forEach(item=>(item.draftServiceKind==='maintenance'?ms:bs).put(item));
      tr.oncomplete=()=>{scheduleCentralSync();resolve();};tr.onerror=()=>reject(tr.error||new Error('Serviceconcept opslaan mislukt.'));tr.onabort=()=>reject(tr.error||new Error('Serviceconcept opslaan afgebroken.'));
    });
  }

  async function refreshVisitState() {
    state.maintenance=await getAll('maintenance');state.breakdowns=await getAll('breakdowns');renderServiceVisits();
  }
  async function syncVisitDraft() {
    if(!navigator.onLine||!window.Clerk?.isSignedIn||typeof window.machineparkSyncOnlineNow!=='function')return false;
    try{await window.machineparkSyncOnlineNow({quiet:true});return true;}catch(e){console.warn('Serviceconcept synchroniseren',e);return false;}
  }
  function setDraftStatus(text,mode='') {
    const el=document.querySelector('#modal .service-visit-draft-status');if(!el)return;el.textContent=text;el.className=`service-visit-draft-status${mode?` ${mode}`:''}`;
  }

  async function saveDraftInternal({manual=false,force=false}={}) {
    const current=activeVisitDraft;if(!current)return null;if(!force&&!current.touched)return{header:current.header,items:current.items};
    setDraftStatus('Concept opslaan…','busy');
    const header=collectHeader(),items=await collectItems();if(activeVisitDraft!==current)return null;
    await writeDraft(header,items);current.header=header;current.items=items;current.persisted=true;current.touched=false;
    await refreshVisitState();const time=new Date().toLocaleTimeString('nl-BE',{hour:'2-digit',minute:'2-digit'});
    setDraftStatus(navigator.onLine?`Concept opgeslagen om ${time} · automatische synchronisatie actief`:`Lokaal opgeslagen om ${time} · synchroniseert zodra internet beschikbaar is`);
    if(manual){const synced=await syncVisitDraft();toast(synced?'Serviceconcept bewaard en gesynchroniseerd':'Serviceconcept bewaard');}
    return{header,items};
  }
  function queueDraftSave(options={}) { const current=activeVisitDraft;visitSaveChain=visitSaveChain.catch(()=>{}).then(()=>activeVisitDraft===current?saveDraftInternal(options):null);return visitSaveChain; }
  function scheduleDraft() { if(!activeVisitDraft||activeVisitDraft.finalizing||activeVisitDraft.restoring)return;activeVisitDraft.touched=true;clearTimeout(visitAutosaveTimer);visitAutosaveTimer=setTimeout(()=>queueDraftSave().catch(e=>{console.warn('Serviceconcept autosave',e);setDraftStatus(e?.message||'Concept opslaan mislukt','error');}),AUTOSAVE_DELAY); }

  function decorateDraftModal() {
    const form=document.getElementById('modalForm'),foot=form?.querySelector('.modal-foot'),submit=form?.querySelector('button[type="submit"]'),cancel=document.getElementById('cancelModal');if(!form||!foot||!submit)return;
    submit.textContent=activeVisitDraft.appendToReportId?'Aanvulling afsluiten':'Serviceverslag afsluiten';
    const status=document.createElement('span');status.className='service-visit-draft-status';status.textContent=activeVisitDraft.persisted?'Concept geladen · wijzigingen worden automatisch opgeslagen.':'Automatisch opslaan start zodra je iets wijzigt.';
    const button=document.createElement('button');button.type='button';button.className='btn service-draft-button';button.textContent='Concept bewaren';button.onclick=async()=>{button.disabled=true;try{activeVisitDraft.touched=true;await queueDraftSave({manual:true,force:true});const current=activeVisitDraft;activeVisitDraft=null;clearTimeout(visitAutosaveTimer);baseCloseModal();if(current)await refreshVisitState();}catch(e){alert(e?.message||'Concept bewaren mislukt.');}finally{if(document.body.contains(button))button.disabled=false;}};
    foot.insertBefore(status,submit);foot.insertBefore(button,submit);if(cancel)cancel.textContent='Sluiten';
    form.addEventListener('input',scheduleDraft);form.addEventListener('change',scheduleDraft);form.addEventListener('click',e=>{if(e.target.closest('.sv-add-part,.sv-add-oneoff,.remove-line,.usage-suggestion,[data-sv-location],[data-kind],[data-fault-pick],[data-add-work-session],[data-remove-work-session]'))scheduleDraft();});
  }

  function stockUpdates(items) {
    const totals={};items.forEach(item=>(item.usedParts||[]).forEach(u=>{const id=String(u?.partId||'').trim(),qty=Number(u?.qty||0);if(id&&qty>0)totals[id]=(totals[id]||0)+qty;}));
    const now=new Date().toISOString(),updates=[];for(const[id,qty]of Object.entries(totals)){const p=(state.parts||[]).find(x=>x.id===id);if(!p)throw new Error(`Onderdeel ${id} bestaat niet meer.`);updates.push({...p,stock:Number(p.stock||0)-qty,updatedAt:now});}return updates;
  }

  function finalRecord(header,item,{visit,serviceVisitId,visitNumberValue,visitRevision,reportId,reportNumberValue,reportRevision,now,batchSize}) {
    const record={...item};['isDraft','draftRole','draftKind','draftBatchId','draftServiceKind','draftLocationKey','draftLocationLabel','draftSchema','targetVisitId'].forEach(k=>delete record[k]);
    const date=header.date||visit?.date||'',time=header.time||visit?.time||'',technician=header.technician||'';
    const locationKey=item.draftLocationKey||visit?.locationKey||'',locationLabel=item.draftLocationLabel||visit?.location||'';
    const locationSessions=header.locationSessions?.[locationKey]||header.workSessions||[];
    const workSessions=(Array.isArray(locationSessions)?locationSessions:[]).filter(row=>row?.date&&Number(row?.minutes)>0).map(row=>({date:String(row.date),minutes:Math.max(1,Math.round(Number(row.minutes)||0))}));
    const totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);
    return {...record,date,time,technician,workSessions,hours:totalMinutes/60,batchId:serviceVisitId,batchSize,updatedAt:now,
      serviceVisitId,serviceVisitNumber:visitNumberValue,serviceVisitLocation:locationLabel,serviceVisitLocationKey:locationKey,serviceVisitDate:date,serviceVisitTime:time,serviceVisitTechnician:technician,serviceVisitStatus:'closed',serviceVisitClosedAt:now,serviceVisitRevision:visitRevision,
      serviceReportId:reportId,serviceReportNumber:reportNumberValue,serviceReportDate:date,serviceReportTime:time,serviceReportTechnician:technician,serviceReportStatus:'closed',serviceReportClosedAt:now,serviceReportRevision:reportRevision};
  }

  function finalizeDraftTransaction(header,allItems,selected,report) {
    const updates=stockUpdates(selected),now=new Date().toISOString(),reportId=report?.id||header.appendToReportId||uid('sr'),reportNumberValue=report?.number||reportNumber(reportId,header.date),reportRevision=report?Math.max(1,Number(report.revision)||1)+1:1;
    const groups=new Map();
    for(const item of selected){const key=String(item.draftLocationKey||header.locationKey||'');if(!key)continue;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(item);}
    const finals=[];
    const visits=[];
    for(const [key,items] of groups){
      const loc=(header.locations||[]).find(x=>x.key===key)||{key,label:items[0]?.draftLocationLabel||''};
      const existing=(report?.visits||[]).find(v=>String(v.locationKey||svKey(v.location))===key)||null;
      const serviceVisitId=existing?.id||loc.visitId||uid('sv');
      const visitNumberValue=existing?.number||visitNumber(serviceVisitId,header.date);
      const visitRevision=existing?Math.max(1,Number(existing.revision)||1)+1:1;
      const visitCtx={id:serviceVisitId,location:loc.label,locationKey:key,date:header.date,time:header.time};
      const built=items.map(item=>finalRecord(header,item,{visit:visitCtx,serviceVisitId,visitNumberValue,visitRevision,reportId,reportNumberValue,reportRevision,now,batchSize:items.length}));
      finals.push(...built);visits.push({id:serviceVisitId,number:visitNumberValue,location:loc.label,locationKey:key,revision:visitRevision,count:built.length});
    }
    return new Promise((resolve,reject)=>{let tr;try{tr=db.transaction(['maintenance','breakdowns','parts'],'readwrite');}catch(e){reject(e);return;}const ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns'),ps=tr.objectStore('parts');updates.forEach(p=>ps.put(p));(header.draftHeaderStore==='maintenance'?ms:bs).delete(header.id);allItems.forEach(i=>(i.draftServiceKind==='maintenance'?ms:bs).delete(i.id));finals.forEach(i=>(i.type!==undefined?ms:bs).put(i));tr.oncomplete=()=>{scheduleCentralSync();resolve({id:reportId,number:reportNumberValue,revision:reportRevision,visits,finals});};tr.onerror=()=>reject(tr.error||new Error('Serviceverslag afsluiten mislukt.'));tr.onabort=()=>reject(tr.error||new Error('Serviceverslag afsluiten afgebroken.'));});
  }

  async function finalizeActiveVisit() {
    const current=activeVisitDraft;if(!current||current.finalizing)return;current.finalizing=true;clearTimeout(visitAutosaveTimer);setDraftStatus('Serviceverslag afsluiten…','busy');
    try{
      current.touched=true;const saved=await queueDraftSave({force:true});if(!saved||activeVisitDraft!==current)return;
      const selected=saved.items,locations=saved.header.locations||[];
      if(!locations.length)throw new Error('Voeg minstens één locatie toe.');
      if(!selected.length)throw new Error('Kies minstens één onderhoud of depannage.');
      const usedLocationKeys=new Set(selected.map(item=>item.draftLocationKey||saved.header.locationKey).filter(Boolean));
      const emptyLocation=locations.find(loc=>!usedLocationKeys.has(loc.key));if(emptyLocation)throw new Error(`Kies minstens één onderhoud of depannage op ${emptyLocation.label} of verwijder die locatie uit het concept.`);
      const missing=selected.find(i=>i.draftServiceKind==='breakdowns'&&!String(i.issue||'').trim());if(missing)throw new Error(`Vul het probleem / de melding in voor ${svDeviceShort(missing.deviceId)}.`);
      const report=saved.header.appendToReportId?serviceReportById(saved.header.appendToReportId):null;
      const result=await finalizeDraftTransaction(saved.header,saved.items,selected,report);
      activeVisitDraft=null;baseCloseModal();await refresh();toast(`Serviceverslag ${result.number} opgeslagen · ${result.visits.length} locatie${result.visits.length===1?'':'s'} · ${result.finals.length} registratie${result.finals.length===1?'':'s'}`);setTimeout(()=>showServiceReportDetails(result.id),0);
    }catch(e){current.finalizing=false;setDraftStatus(e?.message||'Afsluiten mislukt','error');throw e;}
  }

  function headerStoreForUser() { return svCan('breakdowns.add') ? 'breakdowns' : 'maintenance'; }

  async function openServiceVisit(id='',draftId='') {
    if(!svCanCreate()){toast('Deze rol mag geen onderhoud of depannage registreren.');return;}
    if(typeof window.machineparkSyncOnlineNow==='function'&&navigator.onLine&&draftId){try{await window.machineparkSyncOnlineNow({quiet:true});await refreshVisitState();}catch(_){}}
    const header=draftId?visitDraftHeader(draftId):null,items=header?visitDraftItems(header.id):[];
    const requestedReport=id?(serviceReportById(id)||serviceReportForVisit(id)):null;
    const report=requestedReport||(header?.appendToReportId?serviceReportById(header.appendToReportId):null)||(header?.appendToVisitId?serviceReportForVisit(header.appendToVisitId):null);
    if(id&&!report){toast('Serviceverslag niet meer gevonden.');return;}if(!locationGroups().length){toast('Geen actieve toestellen met een locatie gevonden.');return;}
    const draftHeaderStore=header?.draftHeaderStore||headerStoreForUser(),draftKey=header?.id||uid('svdraft');
    const locations=draftLocationList(report,header);
    const activeKey=header?.activeLocationKey||locations[0]?.key||'';
    const activeVisit=report?.visits?.find(v=>String(v.locationKey||svKey(v.location))===activeKey)||report?.visits?.[0]||null;
    activeVisitDraft={id:draftKey,headerStore:draftHeaderStore,header,items,report,locations,activeLocationKey:activeKey,locationSessions:{...(header?.locationSessions||{})},appendToReportId:report?.id||header?.appendToReportId||'',appendToVisitId:activeVisit?.id||header?.appendToVisitId||'',createdAt:header?.createdAt||new Date().toISOString(),persisted:Boolean(header),touched:false,finalizing:false,restoring:Boolean(header)};
    showModal(report?`Serviceverslag aanvullen · ${report.number}`:(header?'Serviceconcept verderzetten':'Nieuw serviceverslag'),serviceVisitForm({report,visit:activeVisit,header,items}),'Serviceverslag afsluiten',async()=>finalizeActiveVisit());
    setTimeout(()=>{initVisitForm({report,visit:activeVisit,header,items});decorateDraftModal();if(activeVisitDraft){activeVisitDraft.restoring=false;activeVisitDraft.touched=false;}},0);
  }

  async function deleteVisitDraft(id) {
    const header=visitDraftHeader(id);if(!header)return;const items=visitDraftItems(id);if(!confirm('Serviceconcept definitief verwijderen? Er wordt geen voorraad aangepast.'))return;
    await new Promise((resolve,reject)=>{const tr=db.transaction(['maintenance','breakdowns'],'readwrite'),ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns');(header.draftHeaderStore==='maintenance'?ms:bs).delete(header.id);items.forEach(i=>(i.draftServiceKind==='maintenance'?ms:bs).delete(i.id));tr.oncomplete=()=>{scheduleCentralSync();resolve();};tr.onerror=()=>reject(tr.error);tr.onabort=()=>reject(tr.error);});await refreshVisitState();await syncVisitDraft();toast('Serviceconcept verwijderd');
  }

  const baseCloseModal = closeModal;
  closeModal = function() {
    const current=activeVisitDraft;if(!current||current.finalizing)return baseCloseModal();clearTimeout(visitAutosaveTimer);
    if(!current.touched&&!current.persisted){activeVisitDraft=null;return baseCloseModal();}
    setDraftStatus('Concept bewaren voor sluiten…','busy');
    queueDraftSave({force:true}).then(()=>syncVisitDraft()).catch(e=>{console.warn('Serviceconcept bewaren bij sluiten',e);toast(e?.message||'Serviceconcept kon niet worden bewaard');}).finally(()=>{if(activeVisitDraft===current)activeVisitDraft=null;baseCloseModal();});
  };
  window.closeModal=closeModal;

  function ensurePrintSheet(){let sheet=document.getElementById('serviceVisitPrintSheet');if(!sheet){sheet=document.createElement('div');sheet.id='serviceVisitPrintSheet';sheet.className='service-visit-print-sheet';document.body.appendChild(sheet);}return sheet;}

  async function printServiceReport(id){
    const report=serviceReportById(id)||serviceReportForVisit(id);if(!report){toast('Serviceverslag niet gevonden.');return;}
    const sheet=ensurePrintSheet();sheet.innerHTML=reportHtml(report);
    const images=[...sheet.querySelectorAll('img')];
    await Promise.all(images.map(img=>img.complete?Promise.resolve():new Promise(resolve=>{const done=()=>resolve();img.addEventListener('load',done,{once:true});img.addEventListener('error',done,{once:true});setTimeout(done,3500);})));
    const title=document.title;document.title=`Machinepark - Serviceverslag - ${report.number}`;document.body.classList.add('service-visit-printing');
    const restore=()=>{document.body.classList.remove('service-visit-printing');document.title=title;window.removeEventListener('afterprint',restore);};
    window.addEventListener('afterprint',restore);window.print();setTimeout(()=>{if(document.body.classList.contains('service-visit-printing'))restore();},1800);
  }

  function showServiceReportDetails(id) {
    const report=serviceReportById(id)||serviceReportForVisit(id);if(!report){toast('Serviceverslag niet gevonden.');return;}
    showModal(`Serviceverslag ${report.number}`,reportHtml(report),'Sluiten',async()=>closeModal());
    setTimeout(()=>{const form=document.getElementById('modalForm'),foot=form?.querySelector('.modal-foot'),cancel=document.getElementById('cancelModal'),submit=form?.querySelector('button[type="submit"]');if(!foot||!submit)return;if(cancel)cancel.style.display='none';submit.textContent='Sluiten';
      if(svCan('print')){const print=document.createElement('button');print.type='button';print.className='btn service-visit-print-btn';print.dataset.serviceReportId=report.id;print.textContent='🖨 Afdrukken';print.onclick=()=>void printServiceReport(report.id);foot.insertBefore(print,submit);
      const mail=document.createElement('button');mail.type='button';mail.className='btn service-visit-mail-btn';mail.dataset.serviceVisitMailId=report.id;mail.dataset.serviceVisitLabel=report.number;mail.textContent='✉ Mail PDF';foot.insertBefore(mail,submit);}
      if(svCanCreate()){
        const addDevice=document.createElement('button');addDevice.type='button';addDevice.className='btn';addDevice.textContent='+ Toestel toevoegen';addDevice.onclick=()=>{baseCloseModal();void openServiceVisit(report.id);};foot.appendChild(addDevice);
        const addLocation=document.createElement('button');addLocation.type='button';addLocation.className='btn primary';addLocation.textContent='+ Locatie toevoegen';addLocation.onclick=()=>{baseCloseModal();void openServiceVisit(report.id);setTimeout(()=>document.getElementById('serviceReportAddLocation')?.click(),80);};submit.classList.remove('primary');foot.appendChild(addLocation);
      }
    },0);
  }

  function showServiceVisitDetails(id) { return showServiceReportDetails(id); }

  function ensurePanel() {
    const work=document.getElementById('view-work');if(!work)return null;let panel=document.getElementById('serviceVisitPanel');if(panel)return panel;
    panel=document.createElement('section');panel.id='serviceVisitPanel';panel.className='service-visit-panel';panel.innerHTML=`<div class="service-visit-panel-head"><div><h3>Serviceverslagen</h3><p>Één verslag kan meerdere locaties bevatten. Onderhoud en depannage blijven per toestel en per locatie opgeslagen.</p></div><button type="button" class="btn primary" id="serviceVisitAdd">+ Serviceverslag</button></div><div id="serviceVisitDraftList"></div><div class="table-wrap"><table class="table service-visit-table"><thead><tr><th>Verslag</th><th>Datum</th><th>Locaties</th><th>Toestellen</th><th>Werkzaamheden</th><th>Technieker</th><th>Status</th><th></th></tr></thead><tbody id="serviceVisitBody"></tbody></table></div>`;
    const drafts=document.getElementById('workDraftPanels');if(drafts?.parentNode===work)drafts.insertAdjacentElement('afterend',panel);else work.insertBefore(panel,work.firstChild);
    document.getElementById('serviceVisitAdd')?.addEventListener('click',()=>void openServiceVisit());
    const m=document.getElementById('workAddMaintenance'),b=document.getElementById('workAddBreakdown');if(m){m.textContent='+ Los onderhoud';m.classList.remove('primary');}if(b){b.textContent='+ Losse depannage';b.classList.remove('primary');}
    return panel;
  }

  function renderServiceVisits() {
    const panel=ensurePanel();if(!panel)return;const add=document.getElementById('serviceVisitAdd');if(add)add.style.display=svCanCreate()?'':'none';
    const draftBox=document.getElementById('serviceVisitDraftList'),headers=visitDraftHeaders();
    if(draftBox)draftBox.innerHTML=headers.length?`<div class="service-visit-drafts"><div class="service-draft-head"><strong>Serviceconcepten (${headers.length})</strong><span class="muted" style="font-size:11px">Meerdere locaties blijven samen in één concept en worden centraal gesynchroniseerd.</span></div><div class="service-draft-list">${headers.map(h=>{const items=visitDraftItems(h.id),locations=Array.isArray(h.locations)&&h.locations.length?h.locations.map(x=>x.label):[h.locationLabel].filter(Boolean),devices=[...new Set(items.map(i=>svDeviceShort(i.deviceId)))].join(', ')||'Nog geen toestel geselecteerd',target=h.appendToReportId?serviceReportById(h.appendToReportId):(h.appendToVisitId?serviceReportForVisit(h.appendToVisitId):null);return `<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${svEsc(target?`Aanvulling ${target.number}`:locations.length?`Serviceverslag · ${locations.length} locatie${locations.length===1?'':'s'}`:'Nieuw serviceverslag')}</div><div class="service-draft-row-meta">${svEsc(locations.join(', ')||'Nog geen locatie')} · ${svEsc(devices)} · laatst aangepast ${svEsc(new Date(h.updatedAt||Date.now()).toLocaleString('nl-BE'))}</div></div><div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-sv-draft-open="${svEsc(h.id)}">Verdergaan</button><button type="button" class="btn small danger" data-sv-draft-delete="${svEsc(h.id)}">Verwijderen</button></div></div>`;}).join('')}</div></div>`:'';
    const body=document.getElementById('serviceVisitBody');if(!body)return;const reports=serviceReports();
    body.innerHTML=reports.length?reports.map(r=>{const acts=[r.maintenanceCount?`${r.maintenanceCount} onderhoud`:'',r.breakdownCount?`${r.breakdownCount} depannage`:''].filter(Boolean).join(' · '),locations=r.visits.map(v=>v.location).filter(Boolean);return `<tr><td><span class="service-visit-number">${svEsc(r.number)}</span><div class="muted" style="font-size:10px">v${svEsc(r.revision)}</div></td><td>${svEsc(svDateText(r.date))}${r.time?`<div class="muted" style="font-size:10px">${svEsc(r.time)}</div>`:''}</td><td><strong>${svEsc(r.locationCount)}</strong><div class="muted" style="font-size:10px">${svEsc(locations.join(' · ')||'—')}</div></td><td>${svEsc(r.deviceCount)}</td><td>${svEsc(acts||'—')}</td><td>${svEsc(r.technician||'—')}</td><td><span class="service-visit-status">Afgesloten</span></td><td><button type="button" class="btn small" data-service-visit-open="${svEsc(r.id)}">Details</button></td></tr>`;}).join(''):'<tr><td colspan="8"><div class="empty">Nog geen gezamenlijke serviceverslagen. Los onderhoud en losse depannages blijven gewoon in de historiek staan.</div></td></tr>';
  }

  document.addEventListener('click',e=>{const open=e.target.closest('[data-service-visit-open]');if(open){showServiceVisitDetails(open.dataset.serviceVisitOpen);return;}const draft=e.target.closest('[data-sv-draft-open]');if(draft){void openServiceVisit('',draft.dataset.svDraftOpen);return;}const del=e.target.closest('[data-sv-draft-delete]');if(del){void deleteVisitDraft(del.dataset.svDraftDelete);}});

  const baseRenderAll=renderAll;
  renderAll=function(){const result=baseRenderAll();renderServiceVisits();return result;};
  window.renderAll=renderAll;

  window.machineparkServiceVisitPdfModel = function(id) {
    const report=serviceReportById(id)||serviceReportForVisit(id);if(!report)return null;
    const parts=mergedReportParts(report),sessions=reportWorkSessions(report),totalMinutes=sessions.reduce((sum,row)=>sum+row.minutes,0),fields=[
      {label:'Verslag',value:report.number||'—'},{label:'Locaties',value:(report.visits||[]).map(v=>v.location||'—').join('\n')||'—'},{label:'Technieker',value:report.technician||'—'},{label:'Status / versie',value:`Afgesloten · v${report.revision}`},
      {label:'Werkdagen / tijd',value:sessions.length?sessions.map(row=>`${svDateText(row.date)} · ${row.location||'—'} · ${row.minutes} min`).join('\n')+`\nTotaal: ${totalMinutes} min`:'—',full:true}
    ];
    for(const visit of report.visits||[]) {
      fields.push({label:`LOCATIE · ${visit.location||'—'}`,value:`${visit.deviceCount} toestel${visit.deviceCount===1?'':'len'} · ${visit.maintenanceCount} onderhoud · ${visit.breakdownCount} depannage`,full:true});
      for(const row of visit.records) fields.push({label:`${row.kind==='maintenance'?'Onderhoud':'Depannage'} · ${svDeviceShort(row.item.deviceId)}`,value:recordSummary(row.kind,row.item,true),full:true});
      const localParts=mergedVisitParts(visit);fields.push({label:`Onderdelen · ${visit.location||'—'}`,value:localParts.length?localParts.map(p=>`${p.label} × ${p.qty} · ${p.devices.join(', ')}`).join('\n'):'—',full:true});
    }
    fields.push({label:'Totaal gebruikte onderdelen · alle locaties',value:parts.length?parts.map(p=>`${p.label} × ${p.qty} · ${p.devices.join(', ')}`).join('\n'):'—',full:true});
    return {headerTitle:'Machinepark . Serviceverslag',subtitle:`${report.number} · ${report.locationCount} locatie${report.locationCount===1?'':'s'}`,rightText:`${svDateText(report.date)}${report.time?` · ${report.time}`:''}`,filenameTitle:`Serviceverslag_${report.number}`,fields,photos:reportPhotos(report).map(p=>p.src),photoTitle:'Foto’s bij serviceverslag',photoColumns:2,photoMaxHeight:105,timelines:[]};
  };

  window.openMachineparkServiceVisit=openServiceVisit;
  window.showMachineparkServiceVisit=showServiceVisitDetails;
  window.renderMachineparkServiceVisits=renderServiceVisits;
  renderServiceVisits();
})();
