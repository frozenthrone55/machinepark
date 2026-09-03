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
    const canM = svCan('maintenance.add') && !existing.has('maintenance');
    const canB = svCan('breakdowns.add') && !existing.has('breakdowns');
    const machine = [device.brand,device.model].filter(Boolean).join(' ') || 'Geen toestelomschrijving';
    const loc = svLocationForDevice(device);
    return `<div class="service-visit-device breakdown-machine-card" data-service-visit-device="${svEsc(device.id)}" data-breakdown-device="${svEsc(device.id)}">
      <div class="service-visit-device-head"><div><strong>${svEsc(device.assetCode || device.model || 'Toestel')}</strong><small>${svEsc(machine)}${device.serial ? ` · S/N ${svEsc(device.serial)}` : ''}${loc ? ` · ${svEsc(loc)}` : ''}</small><div class="sv-manual-panel manual-inline-panel"></div></div>
        <div class="service-visit-kind-picks"><button type="button" class="btn small sv-manual-btn" data-sv-manuals="${svEsc(device.id)}">📘 Handleidingen</button><label class="${canM ? '' : 'disabled'}"><input type="checkbox" data-kind="maintenance" ${mChecked ? 'checked' : ''} ${canM ? '' : 'disabled'}> Onderhoud${existing.has('maintenance') ? ' · al in verslag' : ''}</label><label class="${canB ? '' : 'disabled'}"><input type="checkbox" class="breakdown-machine-check" data-kind="breakdowns" ${bChecked ? 'checked' : ''} ${canB ? '' : 'disabled'}> Depannage${existing.has('breakdowns') ? ' · al in verslag' : ''}</label></div></div>
      <div class="service-visit-kind-panel ${mChecked ? 'active' : ''}" data-panel-kind="maintenance"><h4>Onderhoud · ${svEsc(device.assetCode || device.model || 'Toestel')}</h4><div class="service-visit-grid"><div><label>Type onderhoud *</label><select class="sv-maintenance-type">${['Halfjaarlijks','Jaarlijks','Op afroep','Maandelijks'].map(v=>`<option ${m.type===v?'selected':''}>${v}</option>`).join('')}</select></div><div class="full"><label>Uitgevoerde werkzaamheden / notitie</label><textarea class="sv-maintenance-notes">${svEsc(m.notes || '')}</textarea></div>${partSection('maintenance',m)}</div></div>
      <div class="service-visit-kind-panel ${bChecked ? 'active' : ''}" data-panel-kind="breakdowns"><h4>Depannage · ${svEsc(device.assetCode || device.model || 'Toestel')}</h4><div class="service-visit-grid"><div><label>Prioriteit</label><select class="sv-breakdown-priority">${['Laag','Normaal','Hoog','Kritiek'].map(v=>`<option ${String(b.priority || 'Normaal')===v?'selected':''}>${v}</option>`).join('')}</select></div><div><label>Status</label><select class="sv-breakdown-status">${['Open','In behandeling','Opgelost'].map(v=>`<option ${String(b.status || 'Open')===v?'selected':''}>${v}</option>`).join('')}</select></div><div class="full"><label>Probleem / melding *</label><textarea class="sv-breakdown-issue breakdown-machine-issue">${svEsc(b.issue || '')}</textarea></div><div class="full"><label>Diagnose</label><textarea class="sv-breakdown-diagnosis">${svEsc(b.diagnosis || '')}</textarea></div><div class="full"><label>Oplossing / uitgevoerde werken</label><textarea class="sv-breakdown-solution breakdown-machine-solution">${svEsc(b.solution || '')}</textarea></div>${partSection('breakdowns',b)}</div></div>
    </div>`;
  }

  function serviceVisitForm({visit=null,header=null,items=[]}={}) {
    const location = visit?.location || header?.locationLabel || '';
    const locationKey = visit?.locationKey || header?.locationKey || '';
    const date = visit?.date || header?.date || todayISO();
    const time = visit?.time || header?.time || nowLocalTime();
    const technician = header?.technician ?? (visit?.technician === '—' ? '' : visit?.technician || '');
    const sessionSource = { date, workSessions:Array.isArray(header?.workSessions) ? header.workSessions : [] };
    const workSessionsHtml = typeof window.machineparkServiceWorkSessionsEditor === 'function'
      ? window.machineparkServiceWorkSessionsEditor(sessionSource, 'servicevisit')
      : `<div class="field full"><label>Werkdagen en tijd</label><input name="workSessionDate" type="date" required value="${svEsc(date)}"><input name="workSessionMinutes" type="number" min="1" step="1" required placeholder="minuten"></div>`;
    return `<div class="form-grid"><div class="service-visit-form-note"><strong>Eén bezoek, één klantverslag.</strong> Onderhoud en depannage worden definitief als aparte records per toestel opgeslagen. Onderdelen blijven per toestel bewaard en worden alleen in het klantverslag samengevoegd.</div>
      ${visit ? `<div class="service-visit-existing"><strong>Aanvulling op ${svEsc(visit.number)} · huidige versie v${svEsc(visit.revision)}</strong><div class="muted" style="font-size:11px;margin-top:3px">Bestaande registraties blijven ongewijzigd. Na afsluiten wordt dit hetzelfde verslag met een hogere versie.</div></div>` : ''}
      <div class="field full"><label>Locatie *</label><div class="maintenance-location-autocomplete"><input id="serviceVisitLocationSearch" type="search" required autocomplete="off" placeholder="Typ locatie of toestelnummer…" value="${svEsc(location)}" ${visit ? 'readonly' : ''}><input id="serviceVisitLocationKey" name="locationKey" type="hidden" value="${svEsc(locationKey)}"><div id="serviceVisitLocationSuggestions" class="maintenance-location-suggestions"></div></div><div id="serviceVisitLocationCount" class="muted" style="font-size:11px;margin-top:4px">${location ? `Locatie: ${svEsc(location)}` : 'Typ een locatie of toestelnummer en kies de locatie uit de lijst.'}</div></div>
      <div class="field"><label>Datum *</label><input name="date" type="date" required value="${svEsc(date)}" ${visit ? 'readonly' : ''}></div><div class="field"><label>Uur *</label><input name="time" type="time" required value="${svEsc(time)}" ${visit ? 'readonly' : ''}></div>
      <div class="field"><label>Technieker</label><input name="technician" value="${svEsc(technician)}"></div>${workSessionsHtml}
      <div class="field full"><div class="section-title">Toestellen op deze locatie</div><div class="muted" style="font-size:11px">Kies per toestel Onderhoud, Depannage of beide. Open indien nodig meteen de passende handleidingen.</div></div>
      <div id="serviceVisitDevices" class="service-visit-device-list"><div class="empty" style="padding:24px">Toestellen laden…</div></div></div>`;
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

  function initVisitForm({visit=null,header=null,items=[]}={}) {
    const input=document.getElementById('serviceVisitLocationSearch'),hidden=document.getElementById('serviceVisitLocationKey'),suggestions=document.getElementById('serviceVisitLocationSuggestions'),form=document.getElementById('modalForm');if(!input||!hidden||!suggestions||!form)return;
    const existingLocation=visit?.location||header?.locationLabel||'';
    if(existingLocation){renderDevices(findGroup(hidden.value,existingLocation),visit,items);}
    if(visit)return;
    const hide=()=>suggestions.classList.remove('show');
    const render=()=>{const matches=matchLocationGroups(input.value);suggestions.innerHTML=matches.length?matches.map(g=>`<button type="button" class="maintenance-location-suggestion" data-sv-location="${svEsc(g.key)}"><strong>${svEsc(g.label)}</strong><small>${g.devices.length} actief toestel${g.devices.length===1?'':'len'}</small></button>`).join(''):'<div class="maintenance-location-empty">Geen locatie of toestelnummer gevonden.</div>';suggestions.classList.add('show');};
    if(!hidden.value)input.setCustomValidity('Kies een locatie uit de zoeklijst.');
    input.addEventListener('focus',render);input.addEventListener('input',()=>{hidden.value='';input.setCustomValidity('Kies een locatie uit de zoeklijst.');renderDevices(null);render();});
    input.addEventListener('keydown',e=>{if(e.key==='Escape')hide();if(e.key==='Enter'&&suggestions.classList.contains('show')){const first=suggestions.querySelector('[data-sv-location]');if(first){e.preventDefault();first.click();}}});
    suggestions.addEventListener('click',e=>{const choice=e.target.closest('[data-sv-location]');if(!choice)return;const group=locationGroups().find(g=>g.key===choice.dataset.svLocation);if(!group)return;hidden.value=group.key;input.value=group.label;input.setCustomValidity('');hide();renderDevices(group,null,items);});
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
    const locationLabel=String(document.getElementById('serviceVisitLocationSearch')?.value||'').trim();
    const fd=new FormData(form);
    const workSessions=typeof window.machineparkCollectWorkSessions==='function'
      ? window.machineparkCollectWorkSessions(fd)
      : [{date:String(fd.get('workSessionDate')||''),minutes:Math.max(0,Math.round(Number(fd.get('workSessionMinutes'))||0))}].filter(row=>row.date&&row.minutes>0);
    return {...(existing||{}),id:activeVisitDraft.id,isDraft:true,draftRole:'header',draftKind:'serviceVisit',draftBatchId:activeVisitDraft.id,draftHeaderStore:activeVisitDraft.headerStore,locationKey:String(document.getElementById('serviceVisitLocationKey')?.value||''),locationLabel,date:String(form?.elements.date?.value||''),time:String(form?.elements.time?.value||''),technician:String(form?.elements.technician?.value||'').trim(),workSessions,appendToVisitId:activeVisitDraft.appendToVisitId||'',createdAt:existing?.createdAt||activeVisitDraft.createdAt||now,updatedAt:now,draftSchema:1};
  }

  async function collectItems() {
    const oldMap=new Map((activeVisitDraft?.items||[]).map(i=>[`${i.draftServiceKind}:${i.deviceId}`,i]));
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
        const base={...(old||{}),id,isDraft:true,draftRole:'item',draftKind:'serviceVisit',draftBatchId:activeVisitDraft.id,draftServiceKind:kind,deviceId,usedParts:collectUsed(panel),oneOffParts:collectOneOff(panel),photos,workOrder,createdAt:old?.createdAt||now,updatedAt:now,draftSchema:1};
        if(kind==='maintenance')out.push({...base,type:panel?.querySelector('.sv-maintenance-type')?.value||'Halfjaarlijks',notes:panel?.querySelector('.sv-maintenance-notes')?.value.trim()||''});
        else out.push({...base,priority:panel?.querySelector('.sv-breakdown-priority')?.value||'Normaal',status:panel?.querySelector('.sv-breakdown-status')?.value||'Open',issue:panel?.querySelector('.sv-breakdown-issue')?.value.trim()||'',diagnosis:panel?.querySelector('.sv-breakdown-diagnosis')?.value.trim()||'',solution:panel?.querySelector('.sv-breakdown-solution')?.value.trim()||'',faultRef:typeof window.machineparkFaultRefFromCard==='function'?window.machineparkFaultRefFromCard(card):old?.faultRef||null});
      }
    }
    return out;
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
    submit.textContent=activeVisitDraft.appendToVisitId?'Aanvulling afsluiten':'Servicebezoek afsluiten';
    const status=document.createElement('span');status.className='service-visit-draft-status';status.textContent=activeVisitDraft.persisted?'Concept geladen · wijzigingen worden automatisch opgeslagen.':'Automatisch opslaan start zodra je iets wijzigt.';
    const button=document.createElement('button');button.type='button';button.className='btn service-draft-button';button.textContent='Concept bewaren';button.onclick=async()=>{button.disabled=true;try{activeVisitDraft.touched=true;await queueDraftSave({manual:true,force:true});const current=activeVisitDraft;activeVisitDraft=null;clearTimeout(visitAutosaveTimer);baseCloseModal();if(current)await refreshVisitState();}catch(e){alert(e?.message||'Concept bewaren mislukt.');}finally{if(document.body.contains(button))button.disabled=false;}};
    foot.insertBefore(status,submit);foot.insertBefore(button,submit);if(cancel)cancel.textContent='Sluiten';
    form.addEventListener('input',scheduleDraft);form.addEventListener('change',scheduleDraft);form.addEventListener('click',e=>{if(e.target.closest('.sv-add-part,.sv-add-oneoff,.remove-line,.usage-suggestion,[data-sv-location],[data-kind],[data-fault-pick],[data-add-work-session],[data-remove-work-session]'))scheduleDraft();});
  }

  function stockUpdates(items) {
    const totals={};items.forEach(item=>(item.usedParts||[]).forEach(u=>{const id=String(u?.partId||'').trim(),qty=Number(u?.qty||0);if(id&&qty>0)totals[id]=(totals[id]||0)+qty;}));
    const now=new Date().toISOString(),updates=[];for(const[id,qty]of Object.entries(totals)){const p=(state.parts||[]).find(x=>x.id===id);if(!p)throw new Error(`Onderdeel ${id} bestaat niet meer.`);updates.push({...p,stock:Number(p.stock||0)-qty,updatedAt:now});}return updates;
  }

  function finalRecord(header,item,visit,revision,number,now,batchSize) {
    const record={...item};['isDraft','draftRole','draftKind','draftBatchId','draftServiceKind','draftSchema'].forEach(k=>delete record[k]);
    const serviceVisitId=visit?.id||header.targetVisitId||uid('sv');
    const date=visit?.date||header.date||'',time=visit?.time||header.time||'',technician=header.technician||'',workSessions=(Array.isArray(header.workSessions)?header.workSessions:[]).filter(row=>row?.date&&Number(row?.minutes)>0).map(row=>({date:String(row.date),minutes:Math.max(1,Math.round(Number(row.minutes)||0))})),totalMinutes=workSessions.reduce((sum,row)=>sum+Number(row.minutes||0),0);
    return {...record,date,time,technician,workSessions,hours:totalMinutes/60,batchId:serviceVisitId,batchSize,updatedAt:now,serviceVisitId,serviceVisitNumber:number,serviceVisitLocation:visit?.location||header.locationLabel||'',serviceVisitLocationKey:visit?.locationKey||header.locationKey||svKey(header.locationLabel||''),serviceVisitDate:date,serviceVisitTime:time,serviceVisitTechnician:technician,serviceVisitStatus:'closed',serviceVisitClosedAt:now,serviceVisitRevision:revision};
  }

  function finalizeDraftTransaction(header,allItems,selected,visit) {
    const updates=stockUpdates(selected),now=new Date().toISOString(),serviceVisitId=visit?.id||header.targetVisitId||uid('sv'),number=visit?.number||visitNumber(serviceVisitId,header.date),revision=visit?Math.max(1,Number(visit.revision)||1)+1:1,batchSize=selected.length;
    const finals=selected.map(item=>finalRecord({...header,targetVisitId:serviceVisitId},item,visit,revision,number,now,batchSize));
    return new Promise((resolve,reject)=>{let tr;try{tr=db.transaction(['maintenance','breakdowns','parts'],'readwrite');}catch(e){reject(e);return;}const ms=tr.objectStore('maintenance'),bs=tr.objectStore('breakdowns'),ps=tr.objectStore('parts');updates.forEach(p=>ps.put(p));(header.draftHeaderStore==='maintenance'?ms:bs).delete(header.id);allItems.forEach(i=>(i.draftServiceKind==='maintenance'?ms:bs).delete(i.id));finals.forEach(i=>(i.type!==undefined?ms:bs).put(i));tr.oncomplete=()=>{scheduleCentralSync();resolve({id:serviceVisitId,number,revision,finals});};tr.onerror=()=>reject(tr.error||new Error('Servicebezoek afsluiten mislukt.'));tr.onabort=()=>reject(tr.error||new Error('Servicebezoek afsluiten afgebroken.'));});
  }

  async function finalizeActiveVisit() {
    const current=activeVisitDraft;if(!current||current.finalizing)return;current.finalizing=true;clearTimeout(visitAutosaveTimer);setDraftStatus('Servicebezoek afsluiten…','busy');
    try{current.touched=true;const saved=await queueDraftSave({force:true});if(!saved||activeVisitDraft!==current)return;const selected=saved.items;if(!saved.header.locationKey&&!saved.header.locationLabel)throw new Error('Kies eerst een locatie.');if(!Array.isArray(saved.header.workSessions)||!saved.header.workSessions.length)throw new Error('Vul minstens één werkdag en geldige werktijd in.');if(!selected.length)throw new Error('Kies minstens één onderhoud of depannage.');const missing=selected.find(i=>i.draftServiceKind==='breakdowns'&&!String(i.issue||'').trim());if(missing)throw new Error(`Vul het probleem / de melding in voor ${svDeviceShort(missing.deviceId)}.`);const visit=saved.header.appendToVisitId?serviceVisitById(saved.header.appendToVisitId):null;const result=await finalizeDraftTransaction(saved.header,saved.items,selected,visit);activeVisitDraft=null;baseCloseModal();await refresh();toast(`Serviceverslag ${result.number} opgeslagen · ${result.finals.length} registratie${result.finals.length===1?'':'s'}`);setTimeout(()=>showServiceVisitDetails(result.id),0);}catch(e){current.finalizing=false;setDraftStatus(e?.message||'Afsluiten mislukt','error');throw e;}
  }

  function headerStoreForUser() { return svCan('breakdowns.add') ? 'breakdowns' : 'maintenance'; }

  async function openServiceVisit(id='',draftId='') {
    if(!svCanCreate()){toast('Deze rol mag geen onderhoud of depannage registreren.');return;}
    if(typeof window.machineparkSyncOnlineNow==='function'&&navigator.onLine&&draftId){try{await window.machineparkSyncOnlineNow({quiet:true});await refreshVisitState();}catch(_){}}
    const header=draftId?visitDraftHeader(draftId):null,items=header?visitDraftItems(header.id):[],visit=id?serviceVisitById(id):(header?.appendToVisitId?serviceVisitById(header.appendToVisitId):null);
    if(id&&!visit){toast('Servicebezoek niet meer gevonden.');return;}if(!locationGroups().length){toast('Geen actieve toestellen met een locatie gevonden.');return;}
    const draftHeaderStore=header?.draftHeaderStore||headerStoreForUser(),draftKey=header?.id||uid('svdraft');
    activeVisitDraft={id:draftKey,headerStore:draftHeaderStore,header,items,appendToVisitId:visit?.id||header?.appendToVisitId||'',createdAt:header?.createdAt||new Date().toISOString(),persisted:Boolean(header),touched:false,finalizing:false,restoring:Boolean(header)};
    showModal(visit?`Toestel toevoegen · ${visit.number}`:(header?'Serviceconcept verderzetten':'Nieuw servicebezoek per locatie'),serviceVisitForm({visit,header,items}),'Servicebezoek afsluiten',async()=>finalizeActiveVisit());
    setTimeout(()=>{initVisitForm({visit,header,items});decorateDraftModal();if(activeVisitDraft){activeVisitDraft.restoring=false;activeVisitDraft.touched=false;}},0);
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
  async function printServiceVisit(id){const visit=serviceVisitById(id);if(!visit){toast('Servicebezoek niet gevonden.');return;}const sheet=ensurePrintSheet();sheet.innerHTML=visitReportHtml(visit);const images=[...sheet.querySelectorAll('img')];await Promise.all(images.map(img=>img.complete?Promise.resolve():new Promise(resolve=>{const done=()=>resolve();img.addEventListener('load',done,{once:true});img.addEventListener('error',done,{once:true});setTimeout(done,3500);})));const title=document.title;document.title=`Machinepark - Serviceverslag - ${visit.number}`;document.body.classList.add('service-visit-printing');const restore=()=>{document.body.classList.remove('service-visit-printing');document.title=title;window.removeEventListener('afterprint',restore);};window.addEventListener('afterprint',restore);window.print();setTimeout(()=>{if(document.body.classList.contains('service-visit-printing'))restore();},1800);}

  function showServiceVisitDetails(id) {
    const visit=serviceVisitById(id);if(!visit){toast('Servicebezoek niet gevonden.');return;}
    showModal(`Servicebezoek ${visit.number}`,visitReportHtml(visit),'Sluiten',async()=>closeModal());
    setTimeout(()=>{const form=document.getElementById('modalForm'),foot=form?.querySelector('.modal-foot'),cancel=document.getElementById('cancelModal'),submit=form?.querySelector('button[type="submit"]');if(!foot||!submit)return;if(cancel)cancel.style.display='none';submit.textContent='Sluiten';
      if(svCan('print')){const print=document.createElement('button');print.type='button';print.className='btn service-visit-print-btn';print.dataset.serviceVisitId=id;print.textContent='🖨 Afdrukken';print.onclick=()=>void printServiceVisit(id);foot.insertBefore(print,submit);
      const mail=document.createElement('button');mail.type='button';mail.className='btn service-visit-mail-btn';mail.dataset.serviceVisitMailId=id;mail.dataset.serviceVisitLabel=visit.number;mail.textContent='✉ Mail PDF';foot.insertBefore(mail,submit);}
      if(svCanCreate()){const add=document.createElement('button');add.type='button';add.className='btn primary';add.textContent='+ Toestel toevoegen';add.onclick=()=>{baseCloseModal();void openServiceVisit(id);};submit.classList.remove('primary');foot.appendChild(add);}
    },0);
  }

  function ensurePanel() {
    const work=document.getElementById('view-work');if(!work)return null;let panel=document.getElementById('serviceVisitPanel');if(panel)return panel;
    panel=document.createElement('section');panel.id='serviceVisitPanel';panel.className='service-visit-panel';panel.innerHTML=`<div class="service-visit-panel-head"><div><h3>Servicebezoeken per locatie</h3><p>Onderhoud en depannage blijven per toestel opgeslagen, met één duidelijk klantverslag.</p></div><button type="button" class="btn primary" id="serviceVisitAdd">+ Servicebezoek</button></div><div id="serviceVisitDraftList"></div><div class="table-wrap"><table class="table service-visit-table"><thead><tr><th>Verslag</th><th>Datum</th><th>Locatie</th><th>Toestellen</th><th>Werkzaamheden</th><th>Technieker</th><th>Status</th><th></th></tr></thead><tbody id="serviceVisitBody"></tbody></table></div>`;
    const drafts=document.getElementById('workDraftPanels');if(drafts?.parentNode===work)drafts.insertAdjacentElement('afterend',panel);else work.insertBefore(panel,work.firstChild);
    document.getElementById('serviceVisitAdd')?.addEventListener('click',()=>void openServiceVisit());
    const m=document.getElementById('workAddMaintenance'),b=document.getElementById('workAddBreakdown');if(m){m.textContent='+ Los onderhoud';m.classList.remove('primary');}if(b){b.textContent='+ Losse depannage';b.classList.remove('primary');}
    return panel;
  }

  function renderServiceVisits() {
    const panel=ensurePanel();if(!panel)return;const add=document.getElementById('serviceVisitAdd');if(add)add.style.display=svCanCreate()?'':'none';
    const draftBox=document.getElementById('serviceVisitDraftList'),headers=visitDraftHeaders();
    if(draftBox)draftBox.innerHTML=headers.length?`<div class="service-visit-drafts"><div class="service-draft-head"><strong>Serviceconcepten (${headers.length})</strong><span class="muted" style="font-size:11px">Automatisch lokaal bewaard en centraal gesynchroniseerd.</span></div><div class="service-draft-list">${headers.map(h=>{const items=visitDraftItems(h.id),devices=[...new Set(items.map(i=>svDeviceShort(i.deviceId)))].join(', ')||'Nog geen toestel geselecteerd',target=h.appendToVisitId?serviceVisitById(h.appendToVisitId):null;return `<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${svEsc(target?`Aanvulling ${target.number}`:h.locationLabel||'Nieuw servicebezoek')}</div><div class="service-draft-row-meta">${svEsc(devices)} · laatst aangepast ${svEsc(new Date(h.updatedAt||Date.now()).toLocaleString('nl-BE'))}</div></div><div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-sv-draft-open="${svEsc(h.id)}">Verdergaan</button><button type="button" class="btn small danger" data-sv-draft-delete="${svEsc(h.id)}">Verwijderen</button></div></div>`;}).join('')}</div></div>`:'';
    const body=document.getElementById('serviceVisitBody');if(!body)return;const visits=serviceVisits();body.innerHTML=visits.length?visits.map(v=>{const acts=[v.maintenanceCount?`${v.maintenanceCount} onderhoud`:'',v.breakdownCount?`${v.breakdownCount} depannage`:''].filter(Boolean).join(' · ');return `<tr><td><span class="service-visit-number">${svEsc(v.number)}</span><div class="muted" style="font-size:10px">v${svEsc(v.revision)}</div></td><td>${svEsc(svDateText(v.date))}${v.time?`<div class="muted" style="font-size:10px">${svEsc(v.time)}</div>`:''}</td><td><strong>${svEsc(v.location||'—')}</strong></td><td>${svEsc(v.deviceCount)}</td><td>${svEsc(acts||'—')}</td><td>${svEsc(v.technician||'—')}</td><td><span class="service-visit-status">Afgesloten</span></td><td><button type="button" class="btn small" data-service-visit-open="${svEsc(v.id)}">Details</button></td></tr>`;}).join(''):'<tr><td colspan="8"><div class="empty">Nog geen gezamenlijke servicebezoeken. Los onderhoud en losse depannages blijven gewoon in de historiek staan.</div></td></tr>';
  }

  document.addEventListener('click',e=>{const open=e.target.closest('[data-service-visit-open]');if(open){showServiceVisitDetails(open.dataset.serviceVisitOpen);return;}const draft=e.target.closest('[data-sv-draft-open]');if(draft){void openServiceVisit('',draft.dataset.svDraftOpen);return;}const del=e.target.closest('[data-sv-draft-delete]');if(del){void deleteVisitDraft(del.dataset.svDraftDelete);}});

  const baseRenderAll=renderAll;
  renderAll=function(){const result=baseRenderAll();renderServiceVisits();return result;};
  window.renderAll=renderAll;

  window.machineparkServiceVisitPdfModel = function(id) {
    const visit=serviceVisitById(id);if(!visit)return null;const parts=mergedVisitParts(visit),sessions=visitWorkSessions(visit),totalMinutes=sessions.reduce((sum,row)=>sum+row.minutes,0);
    return {headerTitle:`Machinepark . Serviceverslag`,subtitle:`${visit.number} · ${visit.location||'—'}`,rightText:`${svDateText(visit.date)}${visit.time?` · ${visit.time}`:''}`,filenameTitle:`Serviceverslag_${visit.number}`,fields:[
      {label:'Verslag',value:visit.number||'—'},{label:'Locatie',value:visit.location||'—'},{label:'Technieker',value:visit.technician||'—'},{label:'Status / versie',value:`Afgesloten · v${visit.revision}`},{label:'Werkdagen / tijd',value:sessions.length?sessions.map(row=>`${svDateText(row.date)} · ${row.minutes} min`).join('\n')+`\nTotaal: ${totalMinutes} min`:'—',full:true},
      ...visit.records.map(row=>({label:`${row.kind==='maintenance'?'Onderhoud':'Depannage'} · ${svDeviceShort(row.item.deviceId)}`,value:recordSummary(row.kind,row.item,true),full:true})),
      {label:'Onderdelen · samengevoegd voor klant',value:parts.length?parts.map(p=>`${p.label} × ${p.qty} · ${p.devices.join(', ')}`).join('\n'):'—',full:true}
    ],photos:visitPhotos(visit).map(p=>p.src),photoTitle:'Foto’s bij servicebezoek',photoColumns:2,photoMaxHeight:105,timelines:[]};
  };
  window.openMachineparkServiceVisit=openServiceVisit;
  window.showMachineparkServiceVisit=showServiceVisitDetails;
  window.renderMachineparkServiceVisits=renderServiceVisits;
  renderServiceVisits();
})();
