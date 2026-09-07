from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="work-orders-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Werkbongegevens ook opnemen in de individuele onderhoudsafdruk.
    print_helper = r'''function servicePrintWorkOrder(record) {
    const workOrder = record?.workOrder;
    if (!workOrder || !Array.isArray(workOrder.fields) || !workOrder.fields.length) return '';
    const fields = workOrder.fields.map((field) => {
      const raw = field?.type === 'checkbox' ? (field.value ? 'Ja' : 'Nee') : field?.value;
      return servicePrintField(field?.label || 'Veld', raw === '' || raw === null || raw === undefined ? '—' : raw, field?.type === 'textarea');
    }).join('');
    return `<div class="service-print-section workorder-print-section"><h2>Werkbon · ${servicePrintEsc(workOrder.templateName || 'Werkbon')} <span style="font-weight:400;color:#666">v${servicePrintEsc(workOrder.templateVersion || 1)}</span></h2><div class="workorder-print-grid">${fields}</div></div>`;
  }

  '''
    replace_once(
        'function servicePrintHtml(kind, record) {',
        print_helper + 'function servicePrintHtml(kind, record) {',
        'werkbonhelper individuele afdruk',
    )
    replace_once(
        '<div class="service-print-grid">${fields}${servicePrintPhotos(record)}</div>',
        '<div class="service-print-grid">${fields}${servicePrintWorkOrder(record)}${servicePrintPhotos(record)}</div>',
        'werkbon in individuele onderhoudsafdruk',
    )

    # Werkbon eveneens in de machinetijdlijn zodat Machinedetails-afdruk alles bevat.
    timeline_helper = r'''function workOrderTimelineHtml(workOrder){
 if(!workOrder||!Array.isArray(workOrder.fields)||!workOrder.fields.length)return '';
 const rows=workOrder.fields.map(field=>{const raw=field?.type==='checkbox'?(field.value?'Ja':'Nee'):field?.value;const value=raw===''||raw===null||raw===undefined?'—':String(raw);return `<div class="timeline-workorder-field"><span>${esc(field?.label||'Veld')}</span><strong>${esc(value)}</strong></div>`}).join('');
 return `<div class="timeline-workorder"><div class="timeline-workorder-title">Werkbon · ${esc(workOrder.templateName||'Werkbon')} <span>v${esc(workOrder.templateVersion||1)}</span></div><div class="timeline-workorder-grid">${rows}</div></div>`
}
'''
    replace_once(
        'function deviceUnifiedTimelineHtml(d){',
        timeline_helper + 'function deviceUnifiedTimelineHtml(d){',
        'werkbonhelper machinetijdlijn',
    )
    replace_once(
        "</p>${deviceTimelinePhotosHtml(m.photos,'Onderhoudsfoto')}",
        "</p>${workOrderTimelineHtml(m.workOrder)}${deviceTimelinePhotosHtml(m.photos,'Onderhoudsfoto')}",
        'werkbon in machinetijdlijn',
    )

    style = f'''
<style {MARKER}>
#workOrderSettingsCard .workorder-settings-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap}}
.workorder-config-page{{position:fixed;inset:0;z-index:2400;background:var(--bg);overflow:auto;padding:24px 28px 50px;display:none}}
.workorder-config-page.show{{display:block}}
.workorder-config-shell{{max-width:1180px;margin:0 auto}}
.workorder-config-head{{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:18px}}
.workorder-config-head h2{{margin:0 0 5px}}
.workorder-config-actions{{display:flex;gap:8px;flex-wrap:wrap}}
.workorder-template-list{{display:grid;gap:12px}}
.workorder-template-card{{background:#fff;border:1px solid var(--line);border-radius:15px;padding:15px;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:14px;align-items:center;box-shadow:0 7px 24px rgba(25,57,48,.05)}}
.workorder-template-card h4{{margin:0 0 4px}}
.workorder-template-meta{{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}}
.workorder-template-actions{{display:flex;gap:7px;flex-wrap:wrap;justify-content:flex-end}}
.workorder-template-fields{{display:grid;gap:9px;margin-top:8px}}
.workorder-template-field{{border:1px solid var(--line);border-radius:12px;padding:10px;background:#fbfcfb;display:grid;grid-template-columns:minmax(160px,1.5fr) 150px minmax(160px,1fr) auto;gap:8px;align-items:center}}
.workorder-template-field input,.workorder-template-field select{{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}}
.workorder-template-field-check{{display:flex;align-items:center;gap:6px;font-size:11px;font-weight:700}}
.workorder-template-field-check input{{width:auto}}
.workorder-template-field-actions{{display:flex;gap:4px}}
.workorder-template-field-actions button{{padding:7px 8px}}
.workorder-maintenance-section{{grid-column:1/-1;border:1px solid #cfdcd7;border-radius:13px;background:#f7faf9;padding:12px;margin-top:4px}}
.workorder-maintenance-head{{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:8px}}
.workorder-maintenance-head strong{{font-size:13px}}
.workorder-maintenance-fields{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;margin-top:10px}}
.workorder-maintenance-field{{display:grid;gap:5px}}
.workorder-maintenance-field.full{{grid-column:1/-1}}
.workorder-maintenance-field label{{font-size:11px;font-weight:750;color:#4f5d57}}
.workorder-maintenance-field input:not([type=checkbox]),.workorder-maintenance-field select,.workorder-maintenance-field textarea{{width:100%;border:1px solid var(--line);border-radius:9px;padding:9px;background:#fff}}
.workorder-maintenance-field textarea{{min-height:78px;resize:vertical}}
.workorder-checkbox{{display:flex!important;align-items:center;gap:8px!important;padding:7px 0}}
.workorder-checkbox input{{width:18px;height:18px}}
.workorder-details{{border:1px solid var(--line);border-radius:12px;padding:12px;background:#f8faf9}}
.workorder-details-head{{font-weight:800;margin-bottom:9px}}
.workorder-details-grid,.timeline-workorder-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px 12px}}
.workorder-details-field,.timeline-workorder-field{{display:grid;gap:2px}}
.workorder-details-field span,.timeline-workorder-field span{{font-size:10px;color:var(--muted);font-weight:700}}
.workorder-details-field strong,.timeline-workorder-field strong{{font-size:12px;white-space:pre-wrap}}
.timeline-workorder{{margin-top:10px;border-top:1px solid var(--line);padding-top:9px}}
.timeline-workorder-title{{font-size:11px;font-weight:800;margin-bottom:7px;color:#34584d}}
.timeline-workorder-title span{{font-weight:500;color:var(--muted)}}
@media(max-width:760px){{
 .workorder-config-page{{padding:16px 12px 38px}}
 .workorder-template-card{{grid-template-columns:1fr}}
 .workorder-template-actions{{justify-content:flex-start}}
 .workorder-template-field{{grid-template-columns:1fr}}
 .workorder-maintenance-fields,.workorder-details-grid,.timeline-workorder-grid{{grid-template-columns:1fr}}
}}
@media print{{
 .workorder-config-page{{display:none!important}}
 .workorder-print-section{{break-inside:auto}}
 .workorder-print-grid{{display:grid;grid-template-columns:1fr 1fr;gap:4mm 7mm}}
 .workorder-print-grid .service-print-field.full{{grid-column:1/-1}}
 .timeline-workorder{{break-inside:avoid}}
 .timeline-workorder-grid{{grid-template-columns:1fr 1fr;gap:2mm 5mm}}
}}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="work-orders-v1">
(() => {
  const WORK_ORDER_URL = '/.netlify/functions/work-order-templates';
  let workOrderTemplates = [];
  let workOrderEtag = null;
  let workOrderLoading = null;

  function canConfigureWorkOrders() {
    return Boolean(window.machineparkAccessReady && String(window.machineparkRole || '') === 'beheerder');
  }

  async function workOrderRequest(options = {}) {
    const headers = await centralHeaders(true);
    const res = await fetch(WORK_ORDER_URL, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(data.error || text || `Werkbonactie mislukt (${res.status})`);
    if (Array.isArray(data.templates)) workOrderTemplates = data.templates;
    if (data.etag !== undefined) workOrderEtag = data.etag || null;
    return data;
  }

  async function loadWorkOrderTemplates(force = false) {
    if (!force && workOrderTemplates.length) return workOrderTemplates;
    if (!force && workOrderLoading) return workOrderLoading;
    workOrderLoading = workOrderRequest().then((data) => data.templates || []).finally(() => { workOrderLoading = null; });
    return workOrderLoading;
  }
  window.machineparkLoadWorkOrderTemplates = loadWorkOrderTemplates;

  function normalizeMatch(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
  }

  function templateMatchesDevice(template, device) {
    const brands = Array.isArray(template?.brands) ? template.brands.map(normalizeMatch).filter(Boolean) : [];
    const models = Array.isArray(template?.models) ? template.models.map(normalizeMatch).filter(Boolean) : [];
    const brand = normalizeMatch(device?.brand);
    const model = normalizeMatch(device?.model);
    const brandMatch = !brands.length || brands.some((item) => brand === item || brand.includes(item) || item.includes(brand));
    const modelMatch = !models.length || models.some((item) => model === item || model.includes(item) || item.includes(model));
    return brandMatch && modelMatch;
  }

  function activeTemplatesForDevice(device) {
    return workOrderTemplates.filter((template) => template?.active !== false).sort((a, b) => {
      const am = templateMatchesDevice(a, device) ? 0 : 1;
      const bm = templateMatchesDevice(b, device) ? 0 : 1;
      return am - bm || String(a.name || '').localeCompare(String(b.name || ''), 'nl-BE');
    });
  }

  function workOrderValueText(field) {
    if (field?.type === 'checkbox') return field.value ? 'Ja' : 'Nee';
    const value = field?.value;
    return value === '' || value === null || value === undefined ? '—' : String(value);
  }

  function workOrderDetailsHtml(workOrder) {
    if (!workOrder || !Array.isArray(workOrder.fields) || !workOrder.fields.length) return '<span class="muted">Geen werkbon gekoppeld.</span>';
    return `<div class="workorder-details"><div class="workorder-details-head">${esc(workOrder.templateName || 'Werkbon')} · versie ${esc(workOrder.templateVersion || 1)}</div><div class="workorder-details-grid">${workOrder.fields.map((field) => `<div class="workorder-details-field"><span>${esc(field.label || 'Veld')}</span><strong>${esc(workOrderValueText(field))}</strong></div>`).join('')}</div></div>`;
  }
  window.machineparkWorkOrderDetailsHtml = workOrderDetailsHtml;

  function templateOptionHtml(template, device) {
    const recommended = templateMatchesDevice(template, device);
    return `<option value="${esc(template.id)}">${recommended ? '★ ' : ''}${esc(template.name)} · v${esc(template.version || 1)}${recommended ? ' · aanbevolen' : ''}</option>`;
  }

  function fieldInputHtml(field, value, prefix) {
    const id = `${prefix}-${field.id}`;
    const required = field.required ? '<span style="color:var(--danger)"> *</span>' : '';
    if (field.type === 'checkbox') {
      return `<div class="workorder-maintenance-field full"><label class="workorder-checkbox"><input type="checkbox" data-workorder-field="${esc(field.id)}" ${value ? 'checked' : ''}><span>${esc(field.label)}${required}</span></label></div>`;
    }
    if (field.type === 'textarea') {
      return `<div class="workorder-maintenance-field full"><label for="${esc(id)}">${esc(field.label)}${required}</label><textarea id="${esc(id)}" data-workorder-field="${esc(field.id)}">${esc(value ?? '')}</textarea></div>`;
    }
    if (field.type === 'select') {
      const options = (Array.isArray(field.options) ? field.options : []).map((option) => `<option value="${esc(option)}" ${String(value ?? '') === String(option) ? 'selected' : ''}>${esc(option)}</option>`).join('');
      return `<div class="workorder-maintenance-field"><label for="${esc(id)}">${esc(field.label)}${required}</label><select id="${esc(id)}" data-workorder-field="${esc(field.id)}"><option value="">— Kies —</option>${options}</select></div>`;
    }
    const type = field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text';
    return `<div class="workorder-maintenance-field"><label for="${esc(id)}">${esc(field.label)}${required}</label><input id="${esc(id)}" type="${type}" data-workorder-field="${esc(field.id)}" value="${esc(value ?? '')}"></div>`;
  }

  function renderWorkOrderFields(editor, definition, savedValues = null) {
    const fieldsBox = editor.querySelector('.workorder-maintenance-fields');
    if (!fieldsBox) return;
    if (!definition || !Array.isArray(definition.fields) || !definition.fields.length) {
      fieldsBox.innerHTML = '<div class="muted">Kies een werkbon om de invulvelden te tonen.</div>';
      editor._activeWorkOrderDefinition = null;
      return;
    }
    const values = new Map((Array.isArray(savedValues) ? savedValues : []).map((field) => [field.id, field.value]));
    const prefix = `wo-${Math.random().toString(36).slice(2, 8)}`;
    fieldsBox.innerHTML = definition.fields.map((field) => fieldInputHtml(field, values.has(field.id) ? values.get(field.id) : '', prefix)).join('');
    editor._activeWorkOrderDefinition = definition;
  }

  function makeWorkOrderEditor(device, savedWorkOrder = null) {
    const editor = document.createElement('div');
    editor.className = 'workorder-maintenance-section';
    editor.dataset.workorderEditor = '1';
    editor._savedWorkOrder = savedWorkOrder || null;
    const templates = activeTemplatesForDevice(device);
    const savedOption = savedWorkOrder
      ? `<option value="__saved__" selected>Bewaarde werkbon · ${esc(savedWorkOrder.templateName || 'Werkbon')} · v${esc(savedWorkOrder.templateVersion || 1)}</option>`
      : '';
    editor.innerHTML = `<div class="workorder-maintenance-head"><strong>Werkbon</strong><span class="muted" style="font-size:10px">Kies de exacte bon voor deze machine</span></div><select class="filter workorder-maintenance-select" style="width:100%"><option value="">Geen werkbon</option>${savedOption}${templates.map((template) => templateOptionHtml(template, device)).join('')}</select><div class="workorder-maintenance-fields"></div>`;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (savedWorkOrder) renderWorkOrderFields(editor, { ...savedWorkOrder, fields: savedWorkOrder.fields || [] }, savedWorkOrder.fields || []);
    else renderWorkOrderFields(editor, null);
    select.addEventListener('change', () => {
      if (select.value === '__saved__' && editor._savedWorkOrder) {
        renderWorkOrderFields(editor, { ...editor._savedWorkOrder, fields: editor._savedWorkOrder.fields || [] }, editor._savedWorkOrder.fields || []);
        return;
      }
      const template = workOrderTemplates.find((item) => item.id === select.value) || null;
      renderWorkOrderFields(editor, template);
    });
    return editor;
  }

  function collectWorkOrder(editor) {
    if (!editor) return null;
    const select = editor.querySelector('.workorder-maintenance-select');
    if (!select || !select.value) return null;
    const definition = editor._activeWorkOrderDefinition;
    if (!definition || !Array.isArray(definition.fields)) return null;
    const snapshotFields = definition.fields.map((field) => {
      const input = editor.querySelector(`[data-workorder-field="${field.id}"]`);
      const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
      if (field.required && (field.type === 'checkbox' ? !value : !String(value).trim())) {
        throw new Error(`Vul het verplichte werkbonveld “${field.label}” in.`);
      }
      return { id: field.id, label: field.label, type: field.type, required: Boolean(field.required), options: Array.isArray(field.options) ? [...field.options] : [], value };
    });
    return {
      templateId: definition.templateId || definition.id || editor._savedWorkOrder?.templateId || '',
      templateName: definition.templateName || definition.name || editor._savedWorkOrder?.templateName || 'Werkbon',
      templateVersion: Number(definition.templateVersion || definition.version || editor._savedWorkOrder?.templateVersion || 1),
      fields: snapshotFields,
      capturedAt: new Date().toISOString(),
    };
  }

  function attachMaintenanceWorkOrders(existingId = '') {
    const modal = document.querySelector('#modal .modal-body');
    if (!modal) return;
    const cards = [...modal.querySelectorAll('.maintenance-machine-card')];
    if (cards.length) {
      cards.forEach((card) => {
        if (card.querySelector('[data-workorder-editor]')) return;
        const deviceId = card.dataset?.maintenanceDevice || '';
        const device = state.devices.find((item) => item.id === deviceId) || {};
        const fields = card.querySelector('.maintenance-machine-fields') || card;
        const editor = makeWorkOrderEditor(device, null);
        fields.appendChild(editor);
        const enabled = card.classList.contains('selected');
        editor.querySelectorAll('input,select,textarea').forEach((el) => { el.disabled = !enabled; });
      });
      return;
    }
    if (modal.querySelector('[data-workorder-editor]')) return;
    const record = existingId ? state.maintenance.find((item) => item.id === existingId) : null;
    const device = state.devices.find((item) => item.id === record?.deviceId) || {};
    const grid = modal.querySelector('.form-grid') || modal;
    grid.appendChild(makeWorkOrderEditor(device, record?.workOrder || null));
  }

  const baseOpenMaintenanceForWorkOrders = openMaintenance;
  openMaintenance = function(id) {
    const result = baseOpenMaintenanceForWorkOrders(id);
    loadWorkOrderTemplates().then(() => {
      setTimeout(() => attachMaintenanceWorkOrders(id || ''), 0);
      setTimeout(() => attachMaintenanceWorkOrders(id || ''), 80);
    }).catch((error) => console.warn('Werkbonnen laden', error));
    return result;
  };
  window.openMaintenance = openMaintenance;

  if (typeof setMaintenanceMachineEnabled === 'function') {
    const baseSetMaintenanceMachineEnabledForWorkOrders = setMaintenanceMachineEnabled;
    setMaintenanceMachineEnabled = function(card, enabled) {
      baseSetMaintenanceMachineEnabledForWorkOrders(card, enabled);
      card?.querySelectorAll('[data-workorder-editor] input,[data-workorder-editor] select,[data-workorder-editor] textarea').forEach((el) => { el.disabled = !enabled; });
    };
  }

  const basePutForWorkOrders = put;
  put = async function(storeName, obj) {
    if (storeName === 'maintenance' && obj) {
      const cards = [...document.querySelectorAll('#modal .maintenance-machine-card')];
      if (!cards.length) {
        const editor = document.querySelector('#modal [data-workorder-editor]');
        if (editor) obj = { ...obj, workOrder: collectWorkOrder(editor) };
      }
    }
    return basePutForWorkOrders(storeName, obj);
  };

  const basePutManyForWorkOrders = putMany;
  putMany = async function(storeName, items) {
    if (storeName === 'maintenance' && Array.isArray(items)) {
      items = items.map((item) => {
        const card = [...document.querySelectorAll('#modal .maintenance-machine-card')].find((candidate) => candidate.dataset?.maintenanceDevice === item.deviceId);
        const editor = card?.querySelector('[data-workorder-editor]');
        return editor ? { ...item, workOrder: collectWorkOrder(editor) } : item;
      });
    }
    return basePutManyForWorkOrders(storeName, items);
  };

  const baseShowMaintenanceDetailsForWorkOrders = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {
    const result = baseShowMaintenanceDetailsForWorkOrders(id);
    setTimeout(() => {
      const record = state.maintenance.find((item) => item.id === id);
      const grid = document.querySelector('#modal .modal-body .form-grid');
      if (!record || !grid || grid.querySelector('.workorder-detail-block')) return;
      const block = document.createElement('div');
      block.className = 'field full workorder-detail-block';
      block.innerHTML = `<label>Werkbon</label>${workOrderDetailsHtml(record.workOrder)}`;
      grid.appendChild(block);
    }, 0);
    return result;
  };
  window.showMaintenanceDetails = showMaintenanceDetails;

  function ensureSettingsCard() {
    let card = document.getElementById('workOrderSettingsCard');
    if (!card) {
      const grid = document.querySelector('#view-settings .settings-grid') || document.querySelector('.settings-grid');
      if (!grid) return null;
      card = document.createElement('div');
      card.className = 'settings-card';
      card.id = 'workOrderSettingsCard';
      card.innerHTML = `<div class="workorder-settings-head"><div><h4>Werkbonnen</h4><p>Maak en beheer verschillende werkbonnen per merk of model. De gekozen bon wordt rechtstreeks in Onderhoud ingevuld en afgedrukt.</p></div><button type="button" class="btn primary" id="configureWorkOrders">Configureren</button></div>`;
      grid.appendChild(card);
      card.querySelector('#configureWorkOrders').onclick = () => openWorkOrderConfigPage();
    }
    card.style.display = canConfigureWorkOrders() ? '' : 'none';
    return card;
  }

  function ensureConfigPage() {
    let page = document.getElementById('workOrderConfigPage');
    if (page) return page;
    page = document.createElement('section');
    page.id = 'workOrderConfigPage';
    page.className = 'workorder-config-page';
    page.innerHTML = `<div class="workorder-config-shell"><div class="workorder-config-head"><div><button type="button" class="btn small" id="closeWorkOrderConfig">← Terug naar Beheer</button><h2 style="margin-top:14px">Werkbonnen configureren</h2><p class="muted">Beheer templates. Oude ingevulde onderhoudsbonnen blijven gekoppeld aan hun oorspronkelijke versie.</p></div><div class="workorder-config-actions"><button type="button" class="btn" id="refreshWorkOrders">Vernieuwen</button><button type="button" class="btn primary" id="newWorkOrderTemplate">+ Nieuwe werkbon</button></div></div><div id="workOrderConfigStatus" class="muted" style="margin-bottom:12px"></div><div id="workOrderTemplateList" class="workorder-template-list"></div></div>`;
    document.body.appendChild(page);
    page.querySelector('#closeWorkOrderConfig').onclick = () => page.classList.remove('show');
    page.querySelector('#refreshWorkOrders').onclick = async () => { await loadWorkOrderTemplates(true); renderWorkOrderTemplateList(); };
    page.querySelector('#newWorkOrderTemplate').onclick = () => openTemplateEditor();
    return page;
  }

  function templateScopeText(template) {
    const parts = [];
    if (template.brands?.length) parts.push(`Merk: ${template.brands.join(', ')}`);
    if (template.models?.length) parts.push(`Model: ${template.models.join(', ')}`);
    return parts.join(' · ') || 'Alle machines';
  }

  function renderWorkOrderTemplateList() {
    const page = ensureConfigPage();
    const list = page.querySelector('#workOrderTemplateList');
    const status = page.querySelector('#workOrderConfigStatus');
    status.textContent = `${workOrderTemplates.length} werkbon${workOrderTemplates.length === 1 ? '' : 'nen'} geconfigureerd`;
    if (!workOrderTemplates.length) {
      list.innerHTML = '<div class="empty"><div class="big">📋</div>Nog geen werkbonnen. Maak de eerste werkbon met “Nieuwe werkbon”.</div>';
      return;
    }
    list.innerHTML = workOrderTemplates.map((template) => `<div class="workorder-template-card"><div><h4>${esc(template.name)}</h4><div class="muted" style="font-size:12px">${esc(template.description || 'Geen omschrijving')}</div><div class="workorder-template-meta"><span class="badge ${template.active !== false ? 'success' : 'gray'}">${template.active !== false ? 'Actief' : 'Inactief'}</span><span class="badge gray">Versie ${esc(template.version || 1)}</span><span class="badge gray">${template.fields?.length || 0} velden</span><span class="badge gray">${esc(templateScopeText(template))}</span></div></div><div class="workorder-template-actions"><button type="button" class="btn small" data-workorder-edit="${esc(template.id)}">Configureren</button><button type="button" class="btn small" data-workorder-copy="${esc(template.id)}">Kopiëren</button><button type="button" class="btn small danger" data-workorder-delete="${esc(template.id)}">Verwijderen</button></div></div>`).join('');
    list.querySelectorAll('[data-workorder-edit]').forEach((button) => button.onclick = () => openTemplateEditor(workOrderTemplates.find((item) => item.id === button.dataset.workorderEdit)));
    list.querySelectorAll('[data-workorder-copy]').forEach((button) => button.onclick = () => {
      const source = workOrderTemplates.find((item) => item.id === button.dataset.workorderCopy);
      if (!source) return;
      openTemplateEditor({ ...source, id: '', name: `${source.name} - kopie`, version: 1, createdAt: '', updatedAt: '' });
    });
    list.querySelectorAll('[data-workorder-delete]').forEach((button) => button.onclick = async () => {
      const template = workOrderTemplates.find((item) => item.id === button.dataset.workorderDelete);
      if (!template || !confirm(`Werkbon “${template.name}” verwijderen? Reeds ingevulde onderhoudsbonnen blijven behouden.`)) return;
      try {
        await workOrderRequest({ method: 'POST', body: JSON.stringify({ action: 'delete-template', templateId: template.id, etag: workOrderEtag }) });
        toast('Werkbon verwijderd');
        renderWorkOrderTemplateList();
      } catch (error) { alert(error.message); }
    });
  }

  async function openWorkOrderConfigPage() {
    if (!canConfigureWorkOrders()) { alert('Alleen een beheerder kan werkbonnen configureren.'); return; }
    const page = ensureConfigPage();
    page.classList.add('show');
    page.querySelector('#workOrderConfigStatus').textContent = 'Werkbonnen laden…';
    try { await loadWorkOrderTemplates(true); renderWorkOrderTemplateList(); }
    catch (error) { page.querySelector('#workOrderConfigStatus').textContent = error.message; }
  }
  window.openWorkOrderConfigPage = openWorkOrderConfigPage;

  function templateFieldRow(field = {}) {
    const row = document.createElement('div');
    row.className = 'workorder-template-field';
    row.dataset.fieldId = field.id || `veld-${crypto.randomUUID()}`;
    row.innerHTML = `<input class="wo-field-label" placeholder="Naam veld" value="${esc(field.label || '')}"><select class="wo-field-type"><option value="text">Tekst</option><option value="textarea">Lange tekst</option><option value="number">Getal</option><option value="date">Datum</option><option value="checkbox">Ja / nee</option><option value="select">Keuzelijst</option></select><input class="wo-field-options" placeholder="Keuzes, gescheiden door komma’s" value="${esc((field.options || []).join(', '))}"><div><label class="workorder-template-field-check"><input type="checkbox" class="wo-field-required" ${field.required ? 'checked' : ''}> Verplicht</label><div class="workorder-template-field-actions"><button class="btn small" type="button" data-move-up title="Omhoog">↑</button><button class="btn small" type="button" data-move-down title="Omlaag">↓</button><button class="btn small danger" type="button" data-remove-field title="Verwijderen">×</button></div></div>`;
    row.querySelector('.wo-field-type').value = field.type || 'text';
    const syncOptions = () => row.querySelector('.wo-field-options').style.display = row.querySelector('.wo-field-type').value === 'select' ? '' : 'none';
    row.querySelector('.wo-field-type').onchange = syncOptions;
    row.querySelector('[data-remove-field]').onclick = () => row.remove();
    row.querySelector('[data-move-up]').onclick = () => row.previousElementSibling && row.parentNode.insertBefore(row, row.previousElementSibling);
    row.querySelector('[data-move-down]').onclick = () => row.nextElementSibling && row.parentNode.insertBefore(row.nextElementSibling, row);
    syncOptions();
    return row;
  }

  function collectTemplateFields(container) {
    return [...container.querySelectorAll('.workorder-template-field')].map((row) => ({
      id: row.dataset.fieldId,
      label: row.querySelector('.wo-field-label').value.trim(),
      type: row.querySelector('.wo-field-type').value,
      required: row.querySelector('.wo-field-required').checked,
      options: row.querySelector('.wo-field-type').value === 'select' ? row.querySelector('.wo-field-options').value.split(',').map((item) => item.trim()).filter(Boolean) : [],
    })).filter((field) => field.label);
  }

  function openTemplateEditor(template = null) {
    if (!canConfigureWorkOrders()) return;
    const editing = Boolean(template?.id && workOrderTemplates.some((item) => item.id === template.id));
    const body = `<div class="form-grid"><div class="field full"><label>Naam werkbon</label><input name="name" maxlength="120" value="${esc(template?.name || '')}" placeholder="bv. Lattiz jaarlijks onderhoud" required></div><div class="field full"><label>Omschrijving</label><textarea name="description" maxlength="500" placeholder="Waarvoor wordt deze werkbon gebruikt?">${esc(template?.description || '')}</textarea></div><div class="field"><label>Merk(en)</label><input name="brands" value="${esc((template?.brands || []).join(', '))}" placeholder="bv. Lattiz, Franke"></div><div class="field"><label>Model(len)</label><input name="models" value="${esc((template?.models || []).join(', '))}" placeholder="optioneel, komma gescheiden"></div><div class="field full"><label style="display:flex;align-items:center;gap:8px"><input type="checkbox" name="active" ${template?.active === false ? '' : 'checked'} style="width:auto"> Actief en beschikbaar in Onderhoud</label></div><div class="field full"><div style="display:flex;justify-content:space-between;gap:10px;align-items:center"><label>Velden op de werkbon</label><button type="button" class="btn small" id="addWorkOrderField">+ Veld toevoegen</button></div><div id="workOrderTemplateFields" class="workorder-template-fields"></div></div></div>`;
    showModal(editing ? `Werkbon configureren · v${template.version || 1}` : 'Nieuwe werkbon', body, 'Werkbon opslaan', async (fd) => {
      try {
        const fields = collectTemplateFields(document.getElementById('workOrderTemplateFields'));
        if (!fields.length) throw new Error('Voeg minstens één veld aan de werkbon toe.');
        const payload = {
          id: editing ? template.id : '',
          name: val(fd, 'name'),
          description: val(fd, 'description'),
          brands: val(fd, 'brands').split(',').map((item) => item.trim()).filter(Boolean),
          models: val(fd, 'models').split(',').map((item) => item.trim()).filter(Boolean),
          active: Boolean(fd.get('active')),
          fields,
        };
        await workOrderRequest({ method: 'POST', body: JSON.stringify({ action: 'save-template', template: payload, etag: workOrderEtag }) });
        closeModal();
        toast(editing ? 'Werkbon bijgewerkt · nieuwe versie gemaakt' : 'Werkbon aangemaakt');
        renderWorkOrderTemplateList();
      } catch (error) { alert(error.message); }
    });
    setTimeout(() => {
      const fields = document.getElementById('workOrderTemplateFields');
      if (!fields) return;
      (template?.fields || []).forEach((field) => fields.appendChild(templateFieldRow(field)));
      if (!fields.children.length) fields.appendChild(templateFieldRow({ type: 'text' }));
      document.getElementById('addWorkOrderField').onclick = () => fields.appendChild(templateFieldRow({ type: 'text' }));
    }, 0);
  }

  const baseApplyOperationalPermissionsForWorkOrders = applyOperationalPermissions;
  applyOperationalPermissions = function() {
    baseApplyOperationalPermissionsForWorkOrders();
    ensureSettingsCard();
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

  setTimeout(() => {
    ensureSettingsCard();
    if (window.Clerk?.isSignedIn) loadWorkOrderTemplates().catch(() => {});
  }, 700);
})();
</script>
'''

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor werkbonnen')
    index = index.replace('</head>', style + '</head>', 1)
    index = index.replace('</body>', script + '</body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Werkbonnen configureren',
    'configureWorkOrders',
    'workOrderTemplates',
    'Bewaarde werkbon',
    'data-workorder-editor',
    'collectWorkOrder',
    "storeName === 'maintenance'",
    'workOrderDetailsHtml',
    'servicePrintWorkOrder',
    'workOrderTimelineHtml',
    'Nieuwe werkbon',
    'workorder-template-field',
    "String(window.machineparkRole || '') === 'beheerder'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: werkbonfunctie ontbreekt ({needle})')

print('[Machinepark] configureerbare werkbonnen geïntegreerd in Beheer, Onderhoud, tijdlijn en afdruk')
