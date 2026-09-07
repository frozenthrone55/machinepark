from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="service-drafts-v1"'

if MARKER not in index:
    feature = r'''
<style data-machinepark-build-fix="service-drafts-v1">
.service-draft-panel{margin:0 0 14px;border:1px solid #d8e2de;border-radius:14px;background:#fffdf5;padding:12px;display:none;box-shadow:0 5px 18px rgba(25,57,48,.04)}
.service-draft-panel.show{display:block}.service-draft-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:9px}.service-draft-head strong{font-size:13px;color:#654f18}.service-draft-list{display:grid;gap:8px}.service-draft-row{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:12px;align-items:center;border:1px solid #eadfbf;border-radius:11px;background:#fff;padding:10px 11px}.service-draft-row-title{font-weight:800;font-size:13px;overflow-wrap:anywhere}.service-draft-row-meta{font-size:11px;color:var(--muted);margin-top:3px;line-height:1.45}.service-draft-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.service-draft-badge{display:inline-flex;align-items:center;padding:2px 7px;border-radius:999px;background:#fff1bc;color:#715615;font-size:10px;font-weight:800;margin-right:6px}.service-draft-save-status{margin-right:auto;font-size:11px;color:var(--muted);padding:4px 0}.service-draft-save-status.busy{color:#715615;font-weight:700}.service-draft-save-status.error{color:var(--danger);font-weight:700}.service-draft-modal-note{grid-column:1/-1;border:1px solid #eadfbf;border-radius:10px;background:#fffaf0;padding:9px 10px;font-size:11px;color:#6a5624}.service-draft-button{border-color:#d8c684;background:#fff9e5;color:#654f18}.service-draft-button:hover{background:#fff1c8}
@media(max-width:700px){.service-draft-row{grid-template-columns:1fr}.service-draft-actions{justify-content:flex-start}.service-draft-panel{padding:10px}.service-draft-save-status{width:100%;order:3}.modal-foot .service-draft-button{order:2}.modal-foot .btn.primary{order:1}}
@media print{.service-draft-panel,.service-draft-modal-note,.service-draft-button,.service-draft-save-status{display:none!important}}
</style>
<script data-machinepark-build-fix="service-drafts-v1">
(() => {
  const AUTOSAVE_DELAY = 1400;
  const SERVICE_KINDS = new Set(['maintenance','breakdowns']);
  let activeDraft = null;
  let autosaveTimer = null;
  let saveChain = Promise.resolve();

  const baseOpenMaintenanceForDrafts = openMaintenance;
  const baseOpenBreakdownForDrafts = openBreakdown;
  const baseCloseModalForDrafts = closeModal;
  const baseRenderAllForDrafts = renderAll;
  const baseRenderGlobalSearchForDrafts = renderGlobalSearchResults;
  const baseDeviceTimelineForDrafts = deviceUnifiedTimelineHtml;

  function kindInfo(kind) {
    return kind === 'maintenance'
      ? { store:'maintenance', singular:'Onderhoud', plural:'onderhoud', prefix:'mnt', headerPrefix:'mntdraft', addPermission:'maintenance.add', view:'maintenance' }
      : { store:'breakdowns', singular:'Depannage', plural:'depannages', prefix:'brk', headerPrefix:'brkdraft', addPermission:'breakdowns.add', view:'breakdowns' };
  }

  function isDraftRecord(item) { return Boolean(item?.isDraft === true); }
  function isDraftHeader(item, kind) { return Boolean(isDraftRecord(item) && item.draftRole === 'header' && item.draftKind === kind); }
  function isDraftItem(item, kind, headerId = '') { return Boolean(isDraftRecord(item) && item.draftRole === 'item' && item.draftKind === kind && (!headerId || item.draftBatchId === headerId)); }
  function draftHeader(kind, id) { return (state[kindInfo(kind).store] || []).find(item => isDraftHeader(item, kind) && item.id === id) || null; }
  function draftItems(kind, headerId) { return (state[kindInfo(kind).store] || []).filter(item => isDraftItem(item, kind, headerId)); }
  function canManageDraft(kind) {
    const permission = kindInfo(kind).addPermission;
    if (window.machineparkAccessReady && typeof window.machineparkHasPermission === 'function') return window.machineparkHasPermission(permission);
    return true;
  }

  function withRegularServiceState(callback) {
    const maintenance = state.maintenance;
    const breakdowns = state.breakdowns;
    state.maintenance = (maintenance || []).filter(item => !isDraftRecord(item));
    state.breakdowns = (breakdowns || []).filter(item => !isDraftRecord(item));
    try { return callback(); }
    finally { state.maintenance = maintenance; state.breakdowns = breakdowns; }
  }

  renderAll = function() {
    withRegularServiceState(() => baseRenderAllForDrafts());
    renderDraftPanels();
  };
  window.renderAll = renderAll;

  renderGlobalSearchResults = function() {
    return withRegularServiceState(() => baseRenderGlobalSearchForDrafts());
  };
  window.renderGlobalSearchResults = renderGlobalSearchResults;

  deviceUnifiedTimelineHtml = function(device) {
    return withRegularServiceState(() => baseDeviceTimelineForDrafts(device));
  };
  window.deviceUnifiedTimelineHtml = deviceUnifiedTimelineHtml;

  function ensureDraftPanel(kind) {
    const info = kindInfo(kind);
    const view = document.getElementById(`view-${info.view}`);
    if (!view) return null;
    let panel = document.getElementById(`${info.store}DraftPanel`);
    if (panel) return panel;
    panel = document.createElement('div');
    panel.id = `${info.store}DraftPanel`;
    panel.className = 'service-draft-panel';
    const table = view.querySelector('.table-wrap');
    if (table) table.parentNode.insertBefore(panel, table);
    else view.appendChild(panel);
    return panel;
  }

  function draftDateText(value) {
    if (!value) return 'nog niet opgeslagen';
    try { return new Date(value).toLocaleString('nl-BE', { dateStyle:'short', timeStyle:'short' }); }
    catch (_) { return String(value); }
  }

  function draftDeviceText(kind, headerId) {
    const selected = draftItems(kind, headerId).filter(item => item.draftSelected !== false);
    const names = selected.map(item => {
      const device = state.devices.find(candidate => candidate.id === item.deviceId);
      return device?.assetCode || device?.model || '';
    }).filter(Boolean);
    if (!names.length) return 'nog geen toestel geselecteerd';
    const first = names.slice(0, 3).join(', ');
    return `${selected.length} toestel${selected.length === 1 ? '' : 'len'}${first ? ` · ${first}${names.length > 3 ? ' …' : ''}` : ''}`;
  }

  function renderDraftPanel(kind) {
    const panel = ensureDraftPanel(kind);
    if (!panel) return;
    const info = kindInfo(kind);
    const headers = (state[info.store] || []).filter(item => isDraftHeader(item, kind)).sort((a,b) => String(b.updatedAt || '').localeCompare(String(a.updatedAt || '')));
    if (!headers.length) { panel.classList.remove('show'); panel.innerHTML = ''; return; }
    const manageable = canManageDraft(kind);
    panel.classList.add('show');
    panel.innerHTML = `<div class="service-draft-head"><strong>Concepten (${headers.length})</strong><span class="muted" style="font-size:11px">Automatisch lokaal bewaard en centraal gesynchroniseerd.</span></div><div class="service-draft-list">${headers.map(header => {
      const location = String(header.locationLabel || '').trim() || 'Nog geen locatie';
      const title = `${location}`;
      const actions = manageable ? `<div class="service-draft-actions"><button type="button" class="btn small service-draft-button" data-service-draft-open="${esc(header.id)}" data-service-draft-kind="${kind}">Verdergaan</button><button type="button" class="btn small danger" data-service-draft-delete="${esc(header.id)}" data-service-draft-kind="${kind}">Verwijderen</button></div>` : '';
      return `<div class="service-draft-row"><div><div class="service-draft-row-title"><span class="service-draft-badge">CONCEPT</span>${esc(title)}</div><div class="service-draft-row-meta">${esc(draftDeviceText(kind, header.id))} · laatst aangepast ${esc(draftDateText(header.updatedAt))}</div></div>${actions}</div>`;
    }).join('')}</div>`;
  }

  function renderDraftPanels() { renderDraftPanel('maintenance'); renderDraftPanel('breakdowns'); }

  function setSaveStatus(text, mode = '') {
    const el = document.querySelector('#modal .service-draft-save-status');
    if (!el) return;
    el.className = `service-draft-save-status${mode ? ` ${mode}` : ''}`;
    el.textContent = text || '';
  }

  function existingItemMap(kind, headerId) {
    return new Map(draftItems(kind, headerId).map(item => [item.deviceId, item]));
  }

  function collectUsedParts(card, kind) {
    const selector = kind === 'maintenance' ? '.maintenance-device-usage-list .usage-row' : '.breakdown-device-usage-list .usage-row';
    return [...card.querySelectorAll(selector)].map(row => ({
      partId: row.querySelector('.usage-part')?.value || '',
      qty: Number(row.querySelector('.usage-qty')?.value || 1),
    })).filter(item => item.partId && item.qty > 0);
  }

  function collectOneOff(card) {
    const root = card.querySelector('.service-oneoff-parts');
    if (typeof window.machineparkCollectServiceOneOff === 'function') return window.machineparkCollectServiceOneOff(root);
    return [];
  }

  function collectWorkOrderLoose(card, existing = null) {
    const editor = card?.querySelector('[data-workorder-editor]');
    if (!editor) return existing || null;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select || !select.value) return null;
    const definition = editor._activeWorkOrderDefinition || editor._savedWorkOrder || existing;
    if (!definition || !Array.isArray(definition.fields)) return existing || null;
    return {
      templateId: definition.templateId || definition.id || editor._savedWorkOrder?.templateId || existing?.templateId || '',
      templateName: definition.templateName || definition.name || editor._savedWorkOrder?.templateName || existing?.templateName || 'Werkbon',
      templateVersion: Number(definition.templateVersion || definition.version || editor._savedWorkOrder?.templateVersion || existing?.templateVersion || 1),
      fields: definition.fields.map(field => {
        const input = editor.querySelector(`[data-workorder-field="${field.id}"]`);
        const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
        return { id:field.id, label:field.label, type:field.type, required:Boolean(field.required), options:Array.isArray(field.options) ? [...field.options] : [], value };
      }),
      capturedAt: new Date().toISOString(),
    };
  }

  function validateWorkOrder(workOrder) {
    if (!workOrder || !Array.isArray(workOrder.fields)) return;
    const missing = workOrder.fields.find(field => field.required && (field.type === 'checkbox' ? !field.value : !String(field.value ?? '').trim()));
    if (missing) throw new Error(`Vul het verplichte werkbonveld “${missing.label || 'Werkbon'}” in.`);
  }

  function oneOffRowHtml(item = {}, disabled = false) {
    const off = disabled ? ' disabled' : '';
    const supplier = esc(String(item.supplier || ''));
    const code = esc(String(item.supplierCode || ''));
    const description = esc(String(item.description || ''));
    const qty = Math.max(1, Math.round(Number(item.qty) || 1));
    return `<div class="service-oneoff-row"><input class="service-oneoff-supplier" type="text" maxlength="120" placeholder="Leverancier" value="${supplier}"${off}><input class="service-oneoff-code" type="text" maxlength="120" placeholder="Leveranciercode" value="${code}"${off}><input class="service-oneoff-description" type="text" maxlength="300" placeholder="Omschrijving" value="${description}"${off}><input class="service-oneoff-qty" type="number" min="1" step="1" inputmode="numeric" aria-label="Aantal" value="${qty}"${off}><button type="button" class="remove-line service-oneoff-remove" data-remove-service-oneoff aria-label="Eenmalig onderdeel verwijderen"${off}>×</button></div>`;
  }

  function restoreOneOff(card, items, enabled) {
    const list = card.querySelector('.service-oneoff-list');
    if (!list) return;
    const rows = Array.isArray(items) && items.length ? items : [{}];
    list.innerHTML = rows.map(item => oneOffRowHtml(item, !enabled)).join('');
  }

  function photoGridHtml(photos) {
    const list = (Array.isArray(photos) ? photos : []).filter(Boolean).slice(0,5);
    if (!list.length) return '<div class="muted" style="font-size:11px;margin:4px 0 8px">Nog geen foto’s toegevoegd.</div>';
    return `<div class="service-photo-grid">${list.map((src,index) => {
      const preview = typeof window.machineparkThumbnailRef === 'function' ? window.machineparkThumbnailRef(src) : src;
      return `<div class="service-photo-item"><img src="${esc(preview)}" data-full-src="${esc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="Verslagfoto ${index+1}"><label><input type="checkbox" class="service-photo-remove" value="${index}"> Verwijderen</label></div>`;
    }).join('')}</div>`;
  }

  function restorePhotoEditor(card, kind, photos, enabled) {
    const editor = card.querySelector('.service-photo-editor');
    if (!editor) return;
    const inputClass = kind === 'maintenance' ? 'maintenance-machine-photos' : 'breakdown-machine-photos';
    editor.innerHTML = `<label>Foto’s bij verslag</label>${photoGridHtml(photos)}<input class="service-photo-files ${inputClass}" type="file" accept="image/*" multiple ${enabled ? '' : 'disabled'}><div class="muted" style="font-size:11px;margin-top:4px">Maximaal 5 foto’s per verslag. Foto’s worden automatisch verkleind en apart opgeslagen.</div><div class="service-photo-selected muted" style="font-size:11px;margin-top:4px"></div>`;
  }

  async function collectDraftPhotos(card, kind, itemId, existingPhotos) {
    const editor = card.querySelector('.service-photo-editor');
    if (!editor) return Array.isArray(existingPhotos) ? existingPhotos : [];
    const existing = (Array.isArray(existingPhotos) ? existingPhotos : []).filter(Boolean).slice(0,5);
    const remove = new Set([...editor.querySelectorAll('.service-photo-remove:checked')].map(input => Number(input.value)));
    const files = [...(editor.querySelector('.service-photo-files')?.files || [])].filter(file => file && file.size);
    if (!remove.size && !files.length) return existing;
    const kept = existing.filter((_,index) => !remove.has(index));
    if (kept.length + files.length > 5) throw new Error('Maximaal 5 foto’s per onderhouds- of depannageconcept.');
    const added = [];
    for (const file of files) added.push(await compressImage(file));
    let photos = [...kept, ...added].filter(Boolean).slice(0,5);
    if (typeof window.machineparkPersistServicePhotos === 'function') photos = await window.machineparkPersistServicePhotos(kindInfo(kind).store, itemId, photos);
    restorePhotoEditor(card, kind, photos, card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true);
    return photos;
  }

  function collectWorkSessionsLoose(form) {
    const rows = [...form.querySelectorAll('.service-work-session-row')].map(row => ({
      date: String(row.querySelector('[name="workSessionDate"]')?.value || ''),
      minutes: Math.max(0, Math.round(Number(row.querySelector('[name="workSessionMinutes"]')?.value || 0))),
    }));
    return rows.filter(row => row.date || row.minutes > 0);
  }

  function collectDraftHeader(kind) {
    const form = document.getElementById('modalForm');
    const info = kindInfo(kind);
    const existing = draftHeader(kind, activeDraft?.id) || activeDraft?.header || null;
    const locationInput = document.getElementById(kind === 'maintenance' ? 'maintenanceLocationSearch' : 'breakdownLocationSearch');
    const locationKey = document.getElementById(kind === 'maintenance' ? 'maintenanceLocationKey' : 'breakdownLocationKey');
    const date = form?.querySelector('[name="date"]')?.value || '';
    const time = form?.querySelector('[name="time"]')?.value || '';
    const technician = form?.querySelector('[name="technician"]')?.value.trim() || '';
    const workSessions = collectWorkSessionsLoose(form);
    const totalMinutes = workSessions.reduce((sum,row) => sum + Number(row.minutes || 0), 0);
    const now = new Date().toISOString();
    return {
      ...(existing || {}), id:activeDraft.id, isDraft:true, draftRole:'header', draftKind:kind, draftBatchId:activeDraft.id,
      locationKey:String(locationKey?.value || ''), locationLabel:String(locationInput?.value || '').trim(),
      date, time, technician, workSessions, hours:totalMinutes / 60,
      createdAt:existing?.createdAt || activeDraft.createdAt || now, updatedAt:now,
      draftSchema:1,
    };
  }

  function cardHasContent(card, kind, existing) {
    const checked = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true;
    if (checked || existing) return true;
    if (kind === 'maintenance') return Boolean(card.querySelector('.maintenance-machine-notes')?.value.trim());
    return Boolean(card.querySelector('.breakdown-machine-issue')?.value.trim() || card.querySelector('.breakdown-machine-diagnosis')?.value.trim() || card.querySelector('.breakdown-machine-solution')?.value.trim());
  }

  async function collectDraftItems(kind) {
    const info = kindInfo(kind);
    const existing = activeDraft.itemByDevice;
    const cards = [...document.querySelectorAll('#modal .maintenance-machine-card')].filter(card => kind === 'maintenance' ? Boolean(card.dataset.maintenanceDevice) : Boolean(card.dataset.breakdownDevice));
    const records = [];
    for (const card of cards) {
      const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
      const old = existing.get(deviceId) || null;
      if (!cardHasContent(card, kind, old)) continue;
      const checked = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked === true;
      const id = old?.id || uid(info.prefix);
      const usedParts = collectUsedParts(card, kind);
      const oneOffParts = collectOneOff(card);
      const photos = await collectDraftPhotos(card, kind, id, old?.photos || []);
      const now = new Date().toISOString();
      let record = {
        ...(old || {}), id, isDraft:true, draftRole:'item', draftKind:kind, draftBatchId:activeDraft.id, draftSelected:checked,
        deviceId, usedParts, oneOffParts, photos, createdAt:old?.createdAt || now, updatedAt:now, draftSchema:1,
      };
      if (kind === 'maintenance') {
        record.type = card.querySelector('.maintenance-machine-type')?.value || 'Halfjaarlijks';
        record.notes = card.querySelector('.maintenance-machine-notes')?.value.trim() || '';
        record.workOrder = collectWorkOrderLoose(card, old?.workOrder || null);
      } else {
        record.priority = card.querySelector('.breakdown-machine-priority')?.value || 'Normaal';
        record.status = card.querySelector('.breakdown-machine-status')?.value || 'Open';
        record.issue = card.querySelector('.breakdown-machine-issue')?.value.trim() || '';
        record.diagnosis = card.querySelector('.breakdown-machine-diagnosis')?.value.trim() || '';
        record.solution = card.querySelector('.breakdown-machine-solution')?.value.trim() || '';
        const holder = card.querySelector('.fault-inline-tools');
        record.faultRef = holder?._machineparkFaultSnapshot || old?.faultRef || null;
      }
      records.push(record);
    }
    return records;
  }

  function writeDraftDirect(kind, header, items) {
    const storeName = kindInfo(kind).store;
    const previousIds = new Set([...activeDraft.itemByDevice.values()].map(item => item.id));
    const keepIds = new Set(items.map(item => item.id));
    return new Promise((resolve,reject) => {
      let tr;
      try { tr = db.transaction(storeName, 'readwrite'); }
      catch (error) { reject(error); return; }
      const store = tr.objectStore(storeName);
      store.put(header);
      items.forEach(item => store.put(item));
      previousIds.forEach(id => { if (!keepIds.has(id)) store.delete(id); });
      tr.oncomplete = () => { scheduleCentralSync(); resolve(); };
      tr.onerror = () => reject(tr.error || new Error('Concept opslaan mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept opslaan afgebroken.'));
    });
  }

  async function refreshDraftState(kind) {
    const storeName = kindInfo(kind).store;
    state[storeName] = await getAll(storeName);
    renderDraftPanels();
  }

  async function saveDraftInternal({ manual = false, force = false } = {}) {
    const current = activeDraft;
    if (!current || !SERVICE_KINDS.has(current.kind)) return null;
    if (!force && !current.touched) return { header:current.header, items:[...current.itemByDevice.values()] };
    setSaveStatus('Concept opslaan…', 'busy');
    const header = collectDraftHeader(current.kind);
    const items = await collectDraftItems(current.kind);
    if (activeDraft !== current) return null;
    await writeDraftDirect(current.kind, header, items);
    current.persisted = true;
    current.touched = false;
    current.header = header;
    current.itemByDevice = new Map(items.map(item => [item.deviceId, item]));
    await refreshDraftState(current.kind);
    const time = new Date().toLocaleTimeString('nl-BE', { hour:'2-digit', minute:'2-digit' });
    setSaveStatus(navigator.onLine ? `Concept opgeslagen om ${time} · automatische synchronisatie actief` : `Lokaal opgeslagen om ${time} · synchroniseert zodra internet beschikbaar is`);
    if (manual) toast(`${kindInfo(current.kind).singular}concept bewaard`);
    return { header, items };
  }

  function queueDraftSave(options = {}) {
    clearTimeout(autosaveTimer);
    const current = activeDraft;
    saveChain = saveChain.catch(() => {}).then(() => {
      if (!current || activeDraft !== current) return null;
      return saveDraftInternal(options);
    });
    return saveChain;
  }

  function scheduleDraftAutosave() {
    if (!activeDraft || activeDraft.finalizing || activeDraft.restoring) return;
    activeDraft.touched = true;
    setSaveStatus('Wijzigingen wachten op autosave…');
    clearTimeout(autosaveTimer);
    autosaveTimer = setTimeout(() => queueDraftSave().catch(error => { console.warn('Concept autosave', error); setSaveStatus(error?.message || 'Concept opslaan mislukt', 'error'); }), AUTOSAVE_DELAY);
  }

  function setUsageRows(card, kind, items, enabled) {
    const list = card.querySelector(kind === 'maintenance' ? '.maintenance-device-usage-list' : '.breakdown-device-usage-list');
    if (!list) return;
    const rows = Array.isArray(items) && items.length ? items : [{partId:'',qty:1}];
    list.innerHTML = rows.map(item => usageRowHtml(item, true)).join('');
    list.querySelectorAll('.usage-search,.usage-qty,.remove-line').forEach(el => { el.disabled = !enabled; });
  }

  function restoreWorkOrder(card, saved, enabled) {
    if (!saved) return;
    const editor = card.querySelector('[data-workorder-editor]');
    if (!editor) return;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select) return;
    editor._savedWorkOrder = saved;
    let option = [...select.options].find(item => item.value === '__saved__');
    if (!option) {
      option = document.createElement('option');
      option.value = '__saved__';
      select.insertBefore(option, select.options[1] || null);
    }
    option.textContent = `Bewaarde werkbon · ${saved.templateName || 'Werkbon'} · v${saved.templateVersion || 1}`;
    select.value = '__saved__';
    select.dispatchEvent(new Event('change', { bubbles:true }));
    editor.querySelectorAll('input,select,textarea').forEach(el => { el.disabled = !enabled; });
  }

  function restoreFaultRef(card, saved) {
    if (!saved) return;
    const holder = card.querySelector('.fault-inline-tools');
    if (!holder) return;
    holder._machineparkFaultSnapshot = saved;
    const selected = holder.querySelector('.fault-picker-selected');
    if (selected) selected.textContent = `Gekoppeld: ${[saved.code, saved.name].filter(Boolean).join(' — ')}`;
  }

  function restoreCard(kind, card, item) {
    if (!item) return;
    const enabled = item.draftSelected !== false;
    const checkbox = card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check');
    if (checkbox) checkbox.checked = enabled;
    if (kind === 'maintenance') {
      const type = card.querySelector('.maintenance-machine-type'); if (type) type.value = item.type || 'Halfjaarlijks';
      const notes = card.querySelector('.maintenance-machine-notes'); if (notes) notes.value = item.notes || '';
    } else {
      const priority = card.querySelector('.breakdown-machine-priority'); if (priority) priority.value = item.priority || 'Normaal';
      const status = card.querySelector('.breakdown-machine-status'); if (status) status.value = item.status || 'Open';
      const issue = card.querySelector('.breakdown-machine-issue'); if (issue) issue.value = item.issue || '';
      const diagnosis = card.querySelector('.breakdown-machine-diagnosis'); if (diagnosis) diagnosis.value = item.diagnosis || '';
      const solution = card.querySelector('.breakdown-machine-solution'); if (solution) solution.value = item.solution || '';
    }
    setUsageRows(card, kind, item.usedParts || [], enabled);
    restoreOneOff(card, item.oneOffParts || [], enabled);
    restorePhotoEditor(card, kind, item.photos || [], enabled);
    if (kind === 'maintenance') setMaintenanceMachineEnabled(card, enabled); else setBreakdownMachineEnabled(card, enabled);
  }

  function draftGroup(kind, header, items) {
    const groups = kind === 'maintenance' ? maintenanceLocationGroups() : breakdownLocationGroups();
    let group = groups.find(candidate => candidate.key === header.locationKey);
    if (!group && header.locationLabel) group = groups.find(candidate => normalizeSearch(candidate.label) === normalizeSearch(header.locationLabel));
    if (!group && items.length) {
      const devices = items.map(item => state.devices.find(device => device.id === item.deviceId)).filter(Boolean);
      if (devices.length) group = { key:header.locationKey || normalizeSearch(header.locationLabel), label:header.locationLabel || deviceLocationAt(devices[0]) || 'Concept', devices };
    }
    return group || null;
  }

  function restoreDraftForm(kind, header, items) {
    const form = document.getElementById('modalForm');
    if (!form) return;
    activeDraft.restoring = true;
    const date = form.querySelector('[name="date"]'); if (date) date.value = header.date || date.value;
    const time = form.querySelector('[name="time"]'); if (time) time.value = header.time || time.value;
    const technician = form.querySelector('[name="technician"]'); if (technician) technician.value = header.technician || '';
    const workRoot = form.querySelector('[data-service-work-sessions]');
    if (workRoot && typeof window.machineparkServiceWorkSessionsEditor === 'function') workRoot.outerHTML = window.machineparkServiceWorkSessionsEditor(header, kind === 'maintenance' ? 'maintenance' : 'breakdown');

    const inputId = kind === 'maintenance' ? 'maintenanceLocationSearch' : 'breakdownLocationSearch';
    const keyId = kind === 'maintenance' ? 'maintenanceLocationKey' : 'breakdownLocationKey';
    const boxId = kind === 'maintenance' ? 'maintenanceLocationDevices' : 'breakdownLocationDevices';
    const countId = kind === 'maintenance' ? 'maintenanceLocationCount' : 'breakdownLocationCount';
    const selectAllId = kind === 'maintenance' ? 'maintenanceSelectAll' : 'breakdownSelectAll';
    const input = document.getElementById(inputId), key = document.getElementById(keyId), box = document.getElementById(boxId), count = document.getElementById(countId), selectAll = document.getElementById(selectAllId);
    if (input) { input.value = header.locationLabel || ''; input.setCustomValidity(header.locationKey || header.locationLabel ? '' : 'Kies een locatie uit de zoeklijst.'); }
    if (key) key.value = header.locationKey || '';
    const group = draftGroup(kind, header, items);
    if (group && box) {
      box.innerHTML = group.devices.map(device => kind === 'maintenance' ? maintenanceMachineCardHtml(device) : breakdownMachineCardHtml(device)).join('');
      if (count) count.textContent = `${group.devices.length} toestel${group.devices.length===1?'':'len'} in concept op ${group.label}`;
      if (selectAll) { selectAll.style.display = ''; selectAll.textContent = 'Alles selecteren'; }
      const byDevice = new Map(items.map(item => [item.deviceId, item]));
      [...box.querySelectorAll('.maintenance-machine-card')].forEach(card => {
        const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
        const item = byDevice.get(deviceId);
        if (item) restoreCard(kind, card, item);
        else if (kind === 'maintenance') setMaintenanceMachineEnabled(card, false); else setBreakdownMachineEnabled(card, false);
      });
      if (selectAll) {
        const cards = [...box.querySelectorAll('.maintenance-machine-card')];
        selectAll.textContent = cards.length && cards.every(card => card.querySelector(kind === 'maintenance' ? '.maintenance-machine-check' : '.breakdown-machine-check')?.checked) ? 'Alles uitvinken' : 'Alles selecteren';
      }
    }
    const delayedRestore = () => {
      const byDevice = new Map(items.map(item => [item.deviceId, item]));
      document.querySelectorAll('#modal .maintenance-machine-card').forEach(card => {
        const deviceId = kind === 'maintenance' ? card.dataset.maintenanceDevice : card.dataset.breakdownDevice;
        const item = byDevice.get(deviceId);
        if (!item) return;
        const enabled = item.draftSelected !== false;
        if (kind === 'maintenance') restoreWorkOrder(card, item.workOrder, enabled);
        else restoreFaultRef(card, item.faultRef);
      });
    };
    setTimeout(delayedRestore, 80);
    setTimeout(delayedRestore, 450);
    if (kind === 'maintenance' && typeof window.machineparkLoadWorkOrderTemplates === 'function') Promise.resolve(window.machineparkLoadWorkOrderTemplates()).then(() => setTimeout(delayedRestore,0)).catch(() => {});
    setTimeout(() => { if (activeDraft) { activeDraft.restoring = false; activeDraft.touched = false; } }, 520);
  }

  function decorateDraftModal(kind, header = null) {
    const form = document.getElementById('modalForm');
    const foot = document.querySelector('#modal .modal-foot');
    if (!form || !foot) return false;
    const submit = foot.querySelector('button[type="submit"]');
    const cancel = document.getElementById('cancelModal');
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn service-draft-button';
    button.id = 'saveServiceDraft';
    button.textContent = 'Concept bewaren';
    const status = document.createElement('span');
    status.className = 'service-draft-save-status';
    status.textContent = header ? `Concept geladen · laatst aangepast ${draftDateText(header.updatedAt)}` : 'Automatisch opslaan start zodra je iets wijzigt.';
    foot.insertBefore(status, submit || null);
    foot.insertBefore(button, submit || null);
    if (cancel) cancel.textContent = 'Sluiten';
    const note = document.createElement('div');
    note.className = 'service-draft-modal-note';
    note.textContent = 'Concept: onderdelen worden nog niet van de voorraad afgeboekt en deze registratie komt nog niet in de toestelgeschiedenis. Dat gebeurt pas bij definitief registreren.';
    const grid = form.querySelector('.form-grid');
    if (grid) grid.insertBefore(note, grid.firstChild);
    button.onclick = async () => {
      button.disabled = true;
      try {
        activeDraft.touched = true;
        await queueDraftSave({ manual:true, force:true });
        const current = activeDraft;
        activeDraft = null;
        clearTimeout(autosaveTimer);
        baseCloseModalForDrafts();
        if (current) await refreshDraftState(current.kind);
      } catch (error) {
        console.error(error);
        alert(error?.message || 'Concept opslaan mislukt.');
      } finally { if (document.body.contains(button)) button.disabled = false; }
    };
    form.addEventListener('input', scheduleDraftAutosave);
    form.addEventListener('change', scheduleDraftAutosave);
    form.addEventListener('click', event => {
      if (event.target.closest('[data-fault-pick],[data-add-work-session],[data-remove-work-session],[data-add-service-oneoff],[data-remove-service-oneoff],.remove-line,.maintenance-location-suggestion,.usage-suggestion,.fault-inline-toggle')) scheduleDraftAutosave();
    });
    form.onsubmit = event => { event.preventDefault(); finalizeActiveDraft().catch(error => { console.error(error); alert(error?.message || 'Registreren mislukt.'); }); };
    return true;
  }

  function beginDraftMode(kind, header = null) {
    const items = header ? draftItems(kind, header.id) : [];
    activeDraft = {
      kind, id:header?.id || uid(kindInfo(kind).headerPrefix), header:header || null,
      itemByDevice:new Map(items.map(item => [item.deviceId,item])), createdAt:header?.createdAt || new Date().toISOString(),
      persisted:Boolean(header), touched:false, finalizing:false, restoring:false,
    };
    if (!decorateDraftModal(kind, header)) { activeDraft = null; return; }
    if (header) restoreDraftForm(kind, header, items);
  }

  function openNewDraftCapable(kind) {
    const result = kind === 'maintenance' ? baseOpenMaintenanceForDrafts() : baseOpenBreakdownForDrafts();
    setTimeout(() => beginDraftMode(kind, null), 0);
    return result;
  }

  function openSavedDraft(kind, id) {
    const header = draftHeader(kind, id);
    if (!header) { toast('Concept niet meer gevonden'); return; }
    if (!canManageDraft(kind)) { toast('Deze rol mag dit concept niet verderzetten'); return; }
    const result = kind === 'maintenance' ? baseOpenMaintenanceForDrafts() : baseOpenBreakdownForDrafts();
    setTimeout(() => beginDraftMode(kind, header), 0);
    return result;
  }

  openMaintenance = function(id) {
    if (id && draftHeader('maintenance', id)) return openSavedDraft('maintenance', id);
    if (!id) return openNewDraftCapable('maintenance');
    return baseOpenMaintenanceForDrafts(id);
  };
  window.openMaintenance = openMaintenance;

  openBreakdown = function(id) {
    if (id && draftHeader('breakdowns', id)) return openSavedDraft('breakdowns', id);
    if (!id) return openNewDraftCapable('breakdowns');
    return baseOpenBreakdownForDrafts(id);
  };
  window.openBreakdown = openBreakdown;

  function validateFinalHeader(kind, header, items) {
    const selected = items.filter(item => item.draftSelected !== false);
    if (!header.locationKey && !header.locationLabel) throw new Error('Kies eerst een locatie.');
    if (!selected.length) throw new Error(`Selecteer minstens één toestel voor ${kind === 'maintenance' ? 'het onderhoud' : 'de depannage'}.`);
    const sessions = (header.workSessions || []).filter(row => row.date || Number(row.minutes) > 0);
    if (!sessions.length || sessions.some(row => !row.date || Number(row.minutes) <= 0)) throw new Error('Vul voor elke werkdag een datum en een geldige werkduur in.');
    if (kind === 'breakdowns') {
      const missing = selected.find(item => !String(item.issue || '').trim());
      if (missing) throw new Error(`Vul het probleem / de melding in voor ${deviceName(missing.deviceId) || 'elk geselecteerd toestel'}.`);
    } else selected.forEach(item => validateWorkOrder(item.workOrder));
    return selected;
  }

  function partUpdatesForFinal(items) {
    const totals = {};
    items.forEach(item => (item.usedParts || []).forEach(usage => {
      const id = String(usage?.partId || '').trim();
      const qty = Number(usage?.qty || 0);
      if (id && qty > 0) totals[id] = (totals[id] || 0) + qty;
    }));
    const now = new Date().toISOString();
    const updates = [];
    for (const [id,qty] of Object.entries(totals)) {
      const part = state.parts.find(item => item.id === id);
      if (!part) throw new Error(`Onderdeel ${id} bestaat niet meer. Controleer het concept.`);
      if (Number(part.stock || 0) < qty) throw new Error(`Onvoldoende voorraad voor ${part.artNr || part.description || id} (${Number(part.stock || 0)} beschikbaar, ${qty} nodig).`);
      updates.push({ ...part, stock:Number(part.stock || 0) - qty, updatedAt:now });
    }
    return updates;
  }

  function regularRecordFromDraft(kind, header, item, batchId, batchSize, now) {
    const record = { ...item };
    ['isDraft','draftRole','draftKind','draftBatchId','draftSelected','draftSchema'].forEach(key => delete record[key]);
    record.batchId = batchId;
    if (kind === 'breakdowns') record.batchSize = batchSize;
    record.date = header.date || '';
    record.time = header.time || '';
    record.technician = header.technician || '';
    record.workSessions = (header.workSessions || []).filter(row => row.date && Number(row.minutes) > 0).map(row => ({ date:row.date, minutes:Math.round(Number(row.minutes)) }));
    record.hours = record.workSessions.reduce((sum,row) => sum + Number(row.minutes || 0), 0) / 60;
    record.createdAt = item.createdAt || header.createdAt || now;
    record.updatedAt = now;
    return record;
  }

  function finalizeDraftTransaction(kind, header, allItems, selected) {
    const info = kindInfo(kind);
    const stockUpdates = partUpdatesForFinal(selected);
    const now = new Date().toISOString();
    const batchId = uid(kind === 'maintenance' ? 'mntbatch' : 'brkbatch');
    const finalRecords = selected.map(item => regularRecordFromDraft(kind, header, item, batchId, selected.length, now));
    const selectedIds = new Set(selected.map(item => item.id));
    return new Promise((resolve,reject) => {
      let tr;
      try { tr = db.transaction([info.store,'parts'], 'readwrite'); }
      catch (error) { reject(error); return; }
      const serviceStore = tr.objectStore(info.store);
      const partsStore = tr.objectStore('parts');
      stockUpdates.forEach(part => partsStore.put(part));
      finalRecords.forEach(record => serviceStore.put(record));
      serviceStore.delete(header.id);
      allItems.forEach(item => { if (!selectedIds.has(item.id)) serviceStore.delete(item.id); });
      tr.oncomplete = () => { scheduleCentralSync(); resolve({ records:finalRecords, stockUpdates }); };
      tr.onerror = () => reject(tr.error || new Error('Concept afronden mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept afronden afgebroken.'));
    });
  }

  async function finalizeActiveDraft() {
    const current = activeDraft;
    if (!current || current.finalizing) return;
    const form = document.getElementById('modalForm');
    if (!form) return;
    const submit = form.querySelector('button[type="submit"]');
    const oldText = submit?.textContent || 'Registreren';
    current.finalizing = true;
    clearTimeout(autosaveTimer);
    if (submit) { submit.disabled = true; submit.textContent = 'Registreren…'; }
    try {
      current.touched = true;
      await saveChain.catch(() => {});
      const saved = await saveDraftInternal({ force:true });
      if (!saved || activeDraft !== current) return;
      const selected = validateFinalHeader(current.kind, saved.header, saved.items);
      await finalizeDraftTransaction(current.kind, saved.header, saved.items, selected);
      activeDraft = null;
      baseCloseModalForDrafts();
      await refresh();
      toast(`${selected.length} ${current.kind === 'maintenance' ? 'onderhoudsregistratie' : 'depannageregistratie'}${selected.length === 1 ? '' : 's'} opgeslagen`);
    } catch (error) {
      current.finalizing = false;
      setSaveStatus(error?.message || 'Registreren mislukt', 'error');
      throw error;
    } finally {
      if (submit && document.body.contains(submit)) { submit.disabled = false; submit.textContent = oldText; }
    }
  }

  async function deleteDraft(kind, id) {
    const header = draftHeader(kind, id);
    if (!header) return;
    if (!canManageDraft(kind)) { toast('Deze rol mag dit concept niet verwijderen'); return; }
    const items = draftItems(kind, id);
    if (!confirm(`${kindInfo(kind).singular}concept definitief verwijderen? Er wordt geen voorraad aangepast.`)) return;
    const storeName = kindInfo(kind).store;
    await new Promise((resolve,reject) => {
      const tr = db.transaction(storeName, 'readwrite');
      const store = tr.objectStore(storeName);
      store.delete(header.id); items.forEach(item => store.delete(item.id));
      tr.oncomplete = () => { scheduleCentralSync(); resolve(); };
      tr.onerror = () => reject(tr.error || new Error('Concept verwijderen mislukt.'));
      tr.onabort = () => reject(tr.error || new Error('Concept verwijderen afgebroken.'));
    });
    await refreshDraftState(kind);
    toast('Concept verwijderd');
  }

  closeModal = function() {
    const current = activeDraft;
    if (!current || current.finalizing) return baseCloseModalForDrafts();
    clearTimeout(autosaveTimer);
    if (!current.touched) { activeDraft = null; return baseCloseModalForDrafts(); }
    const modal = document.getElementById('modal');
    modal?.querySelectorAll('button').forEach(button => { button.disabled = true; });
    setSaveStatus('Concept bewaren voor sluiten…', 'busy');
    queueDraftSave({ force:true }).catch(error => {
      console.error('Concept bewaren bij sluiten', error);
      toast(error?.message || 'Concept kon niet worden bewaard');
    }).finally(() => {
      if (activeDraft === current) activeDraft = null;
      baseCloseModalForDrafts();
    });
  };
  window.closeModal = closeModal;

  document.addEventListener('click', event => {
    const open = event.target.closest('[data-service-draft-open]');
    if (open) { event.preventDefault(); openSavedDraft(open.dataset.serviceDraftKind, open.dataset.serviceDraftOpen); return; }
    const remove = event.target.closest('[data-service-draft-delete]');
    if (remove) { event.preventDefault(); deleteDraft(remove.dataset.serviceDraftKind, remove.dataset.serviceDraftDelete).catch(error => alert(error?.message || 'Concept verwijderen mislukt.')); }
  });

  renderDraftPanels();
})();
</script>
'''
    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor serviceconcepten')
    index = index[:pos] + feature + '\n' + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Concept bewaren',
    'AUTOSAVE_DELAY = 1400',
    "draftKind:'header'" if False else "draftRole:'header'",
    "draftRole:'item'",
    'draftSelected',
    'machineparkPersistServicePhotos',
    'collectWorkOrderLoose',
    'fault-inline-tools',
    'finalizeDraftTransaction',
    "db.transaction([info.store,'parts'], 'readwrite')",
    'Automatisch lokaal bewaard en centraal gesynchroniseerd.',
    'onderdelen worden nog niet van de voorraad afgeboekt',
    'withRegularServiceState',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: serviceconcept ontbreekt ({needle})')

print('[Machinepark] concepten met autosave voor onderhoud en depannages actief')
