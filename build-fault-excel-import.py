from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
endpoint_path = ROOT / 'netlify/functions/fault-library.mjs'

index = index_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')

MARKER = 'data-machinepark-build-fix="fault-excel-import-v1"'
CARD_MARKER = 'id="faultExcelImportCard"'

card = r'''
        <div class="settings-card" id="faultExcelImportCard">
          <h4>Storingsbibliotheek · Excel</h4>
          <p>Importeer meerdere storingen tegelijk. Nieuwe storingen worden toegevoegd en herkenbare bestaande storingen worden bijgewerkt. Storingen die niet in het Excel-bestand staan, blijven behouden.</p>
          <input type="file" id="faultExcelFile" accept=".xlsx,.csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/csv" style="display:none">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button class="btn primary" type="button" id="importFaultExcelBtn">Storingen uit Excel importeren</button>
            <button class="btn" type="button" id="downloadFaultExcelTemplateBtn">Excel-sjabloon downloaden</button>
          </div>
          <div class="muted" style="font-size:11px;margin-top:10px;line-height:1.5">Kolommen: <strong>Storingscode</strong> (optioneel), <strong>Storing</strong> (verplicht), Categorie, Merk, Model, Omschrijving, Symptomen, Mogelijke oorzaken, Oplossingen, Opmerkingen en Actief. Gebruik bij meerdere symptomen, oorzaken of oplossingen een puntkomma <strong>;</strong> of een nieuwe regel. Merk en model mogen leeg zijn voor algemene storingen.</div>
        </div>
'''

script = r'''
<script data-machinepark-build-fix="fault-excel-import-v1">
(() => {
  const endpoint = '/.netlify/functions/fault-library';

  function excelFaultNorm(value) {
    return String(value ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function excelFaultKey(fault) {
    return [fault?.code, fault?.name, fault?.brand, fault?.model].map(excelFaultNorm).join('|');
  }

  function excelFaultLines(value) {
    return String(value ?? '').split(/[;\r\n]+/).map(x => x.trim()).filter(Boolean);
  }

  function excelFaultActive(value) {
    const x = excelFaultNorm(value);
    if (!x) return true;
    return !['nee', 'no', 'false', '0', 'inactief', 'inactive', 'uit'].includes(x);
  }

  function excelFaultComparable(fault) {
    return JSON.stringify({
      code: String(fault?.code || '').trim(),
      name: String(fault?.name || '').trim(),
      category: String(fault?.category || '').trim(),
      brand: String(fault?.brand || '').trim(),
      model: String(fault?.brand ? (fault?.model || '') : '').trim(),
      description: String(fault?.description || '').trim(),
      symptoms: Array.isArray(fault?.symptoms) ? fault.symptoms.map(x => String(x).trim()).filter(Boolean) : [],
      causes: Array.isArray(fault?.causes) ? fault.causes.map(x => String(x).trim()).filter(Boolean) : [],
      solutions: Array.isArray(fault?.solutions) ? fault.solutions.map(x => String(x).trim()).filter(Boolean) : [],
      notes: String(fault?.notes || '').trim(),
      active: fault?.active !== false,
    });
  }

  async function faultExcelRequest(options = {}) {
    const headers = await centralHeaders(options.body !== undefined);
    const res = await fetch(endpoint, { cache: 'no-store', ...options, headers: { ...headers, ...(options.headers || {}) } });
    const text = await res.text();
    let data = {};
    try { data = text ? JSON.parse(text) : {}; } catch (_) {}
    if (!res.ok) throw new Error(data.error || text || `Storingsimport mislukt (${res.status})`);
    return data;
  }

  function faultExcelColumn(headers, aliases) {
    return findHeaderIndex(headers, aliases);
  }

  function faultExcelPlan(matrix, currentFaults) {
    let headerRow = -1, headers = [];
    for (let h = 0; h < Math.min(matrix.length, 30); h++) {
      const candidate = (matrix[h] || []).map(cleanCell);
      const name = faultExcelColumn(candidate, ['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem']);
      if (name >= 0) { headerRow = h; headers = candidate; break; }
    }
    if (headerRow < 0) throw new Error('Kolom “Storing” niet gevonden. Download het Machinepark-sjabloon als voorbeeld.');

    const idx = {
      code: faultExcelColumn(headers, ['Storingscode', 'Storingsnummer', 'Foutcode', 'Code', 'Error code']),
      name: faultExcelColumn(headers, ['Storing', 'Storing / korte omschrijving', 'Storingsomschrijving', 'Probleem']),
      category: faultExcelColumn(headers, ['Categorie', 'Category']),
      brand: faultExcelColumn(headers, ['Merk', 'Brand']),
      model: faultExcelColumn(headers, ['Model', 'Toestelmodel']),
      description: faultExcelColumn(headers, ['Omschrijving', 'Beschrijving', 'Description']),
      symptoms: faultExcelColumn(headers, ['Symptomen', 'Symptoms']),
      causes: faultExcelColumn(headers, ['Mogelijke oorzaken', 'Oorzaken', 'Causes']),
      solutions: faultExcelColumn(headers, ['Oplossingen', 'Oplossing', 'Controle / oplossingen', 'Solution']),
      notes: faultExcelColumn(headers, ['Opmerkingen', 'Interne opmerkingen', 'Notities', 'Notes']),
      active: faultExcelColumn(headers, ['Actief', 'Active']),
    };

    const get = (row, key) => idx[key] >= 0 ? cleanCell(row[idx[key]]) : '';
    const existing = new Map();
    (currentFaults || []).forEach(fault => { const key = excelFaultKey(fault); if (!existing.has(key)) existing.set(key, fault); });
    const seen = new Map();
    const records = [];
    const errors = [];

    for (let ri = headerRow + 1; ri < matrix.length; ri++) {
      const row = matrix[ri] || [];
      if (!row.some(value => cleanCell(value))) continue;
      const name = get(row, 'name');
      if (!name) { errors.push({ row: ri + 1, reason: 'Storing ontbreekt' }); continue; }
      const brand = get(row, 'brand');
      const fault = {
        code: get(row, 'code'),
        name,
        category: get(row, 'category'),
        brand,
        model: brand ? get(row, 'model') : '',
        description: get(row, 'description'),
        symptoms: excelFaultLines(get(row, 'symptoms')),
        causes: excelFaultLines(get(row, 'causes')),
        solutions: excelFaultLines(get(row, 'solutions')),
        notes: get(row, 'notes'),
        active: idx.active >= 0 ? excelFaultActive(get(row, 'active')) : true,
      };
      const key = excelFaultKey(fault);
      if (!excelFaultNorm(fault.name)) { errors.push({ row: ri + 1, reason: 'Ongeldige storing' }); continue; }
      if (seen.has(key)) { errors.push({ row: ri + 1, reason: `Dubbele storing in Excel (ook regel ${seen.get(key)})` }); continue; }
      seen.set(key, ri + 1);
      const old = existing.get(key) || null;
      if (!old) records.push({ action: 'add', row: ri + 1, fault });
      else if (excelFaultComparable(old) === excelFaultComparable(fault)) records.push({ action: 'same', row: ri + 1, old, fault: { ...fault, id: old.id } });
      else records.push({ action: 'update', row: ri + 1, old, fault: { ...fault, id: old.id } });
    }
    return { records, errors };
  }

  function faultImportPreview(plan, fileName, etag) {
    const adds = plan.records.filter(r => r.action === 'add');
    const updates = plan.records.filter(r => r.action === 'update');
    const same = plan.records.filter(r => r.action === 'same');
    const changes = [...updates, ...adds];
    const preview = changes.slice(0, 40);
    const rows = preview.map(r => `<tr><td>${r.row}</td><td><span class="badge ${r.action === 'add' ? 'blue' : 'warn'}">${r.action === 'add' ? 'Nieuw' : 'Bijwerken'}</span></td><td><strong>${esc([r.fault.code, r.fault.name].filter(Boolean).join(' — '))}</strong></td><td>${esc(r.fault.brand || 'Alle merken')}${r.fault.model ? ' · ' + esc(r.fault.model) : ''}</td></tr>`).join('');
    const errorRows = plan.errors.slice(0, 12).map(e => `<div class="alert"><strong>Excel-regel ${e.row}</strong>${esc(e.reason)}</div>`).join('');
    const body = `<div class="kpis" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-bottom:14px"><div class="kpi" style="box-shadow:none"><div class="label">Nieuw</div><div class="value">${adds.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Bijwerken</div><div class="value">${updates.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Ongewijzigd</div><div class="value">${same.length}</div></div><div class="kpi" style="box-shadow:none"><div class="label">Fouten</div><div class="value">${plan.errors.length}</div></div></div><div class="alert"><strong>Niet-destructieve import</strong>Storingen die niet in dit bestand staan worden niet verwijderd. Een bestaande storing wordt herkend op combinatie van storingscode + storing + merk + model.</div><div class="muted" style="margin:12px 0">Bestand: ${esc(fileName)} · ${changes.length} wijziging(en) klaar om te verwerken.</div><div class="table-wrap"><table class="table" style="min-width:720px"><thead><tr><th>Regel</th><th>Actie</th><th>Storing</th><th>Toepassing</th></tr></thead><tbody>${rows || '<tr><td colspan="4"><div class="empty">Geen wijzigingen nodig.</div></td></tr>'}${changes.length > preview.length ? `<tr><td colspan="4" class="muted">… en nog ${changes.length - preview.length} wijziging(en)</td></tr>` : ''}</tbody></table></div>${plan.errors.length ? `<div style="margin-top:14px"><div class="section-title">Regels met fouten</div>${errorRows}${plan.errors.length > 12 ? `<div class="muted">… en nog ${plan.errors.length - 12} fout(en)</div>` : ''}</div>` : ''}`;
    $('#modal').innerHTML = `<div class="modal-head"><h3>Storingen uit Excel importeren</h3><button class="close" type="button">×</button></div><div class="modal-body">${body}</div><div class="modal-foot"><button class="btn" type="button" id="cancelFaultExcelImport">Annuleren</button><button class="btn primary" type="button" id="confirmFaultExcelImport" ${changes.length ? '' : 'disabled'}>${changes.length} wijziging${changes.length === 1 ? '' : 'en'} importeren</button></div>`;
    enhanceSortableTables($('#modal'));
    $('#modalBackdrop').classList.add('show');
    $('.close').onclick = closeModal;
    $('#cancelFaultExcelImport').onclick = closeModal;
    const confirmBtn = $('#confirmFaultExcelImport');
    if (confirmBtn) confirmBtn.onclick = async () => {
      confirmBtn.disabled = true;
      confirmBtn.textContent = 'Importeren…';
      try {
        const result = await faultExcelRequest({ method: 'POST', body: JSON.stringify({ action: 'import-faults', etag, faults: changes.map(r => r.fault) }) });
        closeModal();
        if (typeof window.machineparkLoadFaultLibrary === 'function') await window.machineparkLoadFaultLibrary(true).catch(() => {});
        if (typeof window.machineparkRenderFaultLibrary === 'function') window.machineparkRenderFaultLibrary();
        toast(`Storingsimport klaar · ${result.added || 0} nieuw · ${result.updated || 0} bijgewerkt`);
      } catch (error) {
        console.error('Storingen Excel-import', error);
        alert('Storingsimport mislukt: ' + (error?.message || 'onbekende fout'));
        confirmBtn.disabled = false;
        confirmBtn.textContent = `${changes.length} wijziging${changes.length === 1 ? '' : 'en'} importeren`;
      }
    };
  }

  async function importFaultExcel(file) {
    try {
      if (!file) return;
      const [matrix, current] = await Promise.all([readStockMatrix(file), faultExcelRequest()]);
      const plan = faultExcelPlan(matrix, current.faults || []);
      if (!plan.records.length && !plan.errors.length) throw new Error('Geen storingsregels gevonden in het bestand.');
      faultImportPreview(plan, file.name || 'storingen.xlsx', current.etag || null);
    } catch (error) {
      console.error('Storingen Excel inlezen', error);
      alert('Excel-import mislukt: ' + (error?.message || 'onbekende fout'));
    }
  }

  function faultTemplateXmlEsc(value) {
    return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&apos;');
  }

  function faultTemplateCell(ref, value) {
    return `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${faultTemplateXmlEsc(value)}</t></is></c>`;
  }

  function downloadFaultExcelTemplate() {
    try {
      const headers = ['Storingscode','Storing','Categorie','Merk','Model','Omschrijving','Symptomen','Mogelijke oorzaken','Oplossingen','Opmerkingen','Actief'];
      const letters = 'ABCDEFGHIJK'.split('');
      const cells = headers.map((h, i) => faultTemplateCell(`${letters[i]}1`, h)).join('');
      const sheet = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="A1:K1"/><sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews><cols><col min="1" max="1" width="16" customWidth="1"/><col min="2" max="2" width="30" customWidth="1"/><col min="3" max="5" width="20" customWidth="1"/><col min="6" max="10" width="34" customWidth="1"/><col min="11" max="11" width="12" customWidth="1"/></cols><sheetData><row r="1">${cells}</row></sheetData><autoFilter ref="A1:K1"/></worksheet>`;
      const enc = new TextEncoder();
      const files = [
        { name: '[Content_Types].xml', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>') },
        { name: '_rels/.rels', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>') },
        { name: 'xl/workbook.xml', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Storingen" sheetId="1" r:id="rId1"/></sheets></workbook>') },
        { name: 'xl/_rels/workbook.xml.rels', bytes: enc.encode('<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>') },
        { name: 'xl/worksheets/sheet1.xml', bytes: enc.encode(sheet) },
      ];
      const blob = makeStoreZip(files);
      downloadBlob(`Machinepark_Storingen_Sjabloon_${todayISO()}.xlsx`, new Blob([blob], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
      toast('Excel-sjabloon voor storingen gedownload');
    } catch (error) {
      console.error('Storingen Excel-sjabloon', error);
      alert('Excel-sjabloon maken mislukt: ' + (error?.message || 'onbekende fout'));
    }
  }

  const fileInput = document.getElementById('faultExcelFile');
  const importBtn = document.getElementById('importFaultExcelBtn');
  const templateBtn = document.getElementById('downloadFaultExcelTemplateBtn');
  if (importBtn && fileInput) importBtn.addEventListener('click', () => { fileInput.value = ''; fileInput.click(); });
  if (fileInput) fileInput.addEventListener('change', () => importFaultExcel(fileInput.files?.[0]));
  if (templateBtn) templateBtn.addEventListener('click', downloadFaultExcelTemplate);
})();
</script>
'''

if CARD_MARKER not in index:
    anchor = '        <div class="settings-card"><h4>Toestellen synchroniseren</h4>'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: Beheer-anker voor storingsimport {index.count(anchor)}x gevonden')
    index = index.replace(anchor, card + anchor, 1)

if MARKER not in index:
    anchor = '<script>\n// iOS/Chrome-safe navigation bridge.'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: script-anker voor storingsimport {index.count(anchor)}x gevonden')
    index = index.replace(anchor, script + anchor, 1)

helper_marker = '// machinepark-fault-excel-import-server-v1'
if helper_marker not in endpoint:
    helper_anchor = "async function saveConfig(store, config, currentEtag, expectedEtag) {"
    helper = r'''// machinepark-fault-excel-import-server-v1
function faultImportKey(fault) {
  const norm = (value) => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  return [fault?.code, fault?.name, fault?.brand, fault?.model].map(norm).join('|');
}

async function writeImportAudit(store, auth, added, updated, total) {
  try {
    const at = new Date().toISOString();
    const id = crypto.randomUUID();
    const email = primaryEmailOf(auth.user) || auth.sub;
    await store.setJSON(`${AUDIT_PREFIX}${Date.now()}-${id}`, {
      id,
      at,
      userId: auth.sub,
      userEmail: email,
      userName: [auth.user?.firstName, auth.user?.lastName].filter(Boolean).join(' '),
      userRole: auth.role,
      changeCount: Math.max(1, added + updated),
      changes: [{
        entityType: 'Storingen',
        entityId: 'excel-import',
        entityLabel: 'Storingsbibliotheek Excel-import',
        action: 'geïmporteerd',
        fields: [
          { field: 'Nieuwe storingen', before: '—', after: String(added) },
          { field: 'Bijgewerkte storingen', before: '—', after: String(updated) },
          { field: 'Verwerkte Excel-regels', before: '—', after: String(total) },
        ],
      }],
      truncated: false,
    }, { metadata: { at, userId: auth.sub, userEmail: email } });
  } catch (error) {
    console.error('fault excel import audit', error);
  }
}

'''
    if endpoint.count(helper_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: saveConfig-anker niet uniek')
    endpoint = endpoint.replace(helper_anchor, helper + helper_anchor, 1)

action_marker = "if (action === 'import-faults')"
if action_marker not in endpoint:
    action_anchor = "    if (action === 'delete-fault') {"
    action = r'''    if (action === 'import-faults') {
      const incoming = Array.isArray(body?.faults) ? body.faults : [];
      if (!incoming.length) return json({ error: 'Geen storingen ontvangen voor import.' }, 400);
      if (incoming.length > MAX_FAULTS) return json({ error: `Maximaal ${MAX_FAULTS} storingen per import toegestaan.` }, 400);

      const merged = [...config.faults];
      const seen = new Set();
      let added = 0;
      let updated = 0;

      for (const raw of incoming) {
        const requestedId = raw?.id ? cleanId(raw.id) : '';
        const incomingKey = faultImportKey(raw);
        if (!incomingKey || incomingKey === '|||') return json({ error: 'Een geïmporteerde storing heeft geen geldige naam.' }, 400);
        const duplicateKey = requestedId ? `id:${requestedId}` : `key:${incomingKey}`;
        if (seen.has(duplicateKey)) return json({ error: 'De Excel-import bevat dezelfde storing meer dan één keer.' }, 400);
        seen.add(duplicateKey);

        let index = requestedId ? merged.findIndex((item) => item.id === requestedId) : -1;
        if (index < 0) index = merged.findIndex((item) => faultImportKey(item) === incomingKey);
        const existing = index >= 0 ? merged[index] : null;
        const fault = sanitizeFault({ ...raw, id: existing?.id || undefined }, existing);
        if (existing) {
          merged[index] = fault;
          updated++;
        } else {
          merged.push(fault);
          added++;
        }
      }

      if (merged.length > MAX_FAULTS) return json({ error: `De storingsbibliotheek mag maximaal ${MAX_FAULTS} storingen bevatten.` }, 400);
      const saved = await saveConfig(store, { version: 1, faults: merged }, etag, body?.etag || null);
      await writeImportAudit(store, access, added, updated, incoming.length);
      return json({ ok: true, faults: normalizeConfig(saved.data).faults, etag: saved.etag || null, canManage: true, added, updated });
    }

'''
    if endpoint.count(action_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: delete-fault-anker niet uniek')
    endpoint = endpoint.replace(action_anchor, action + action_anchor, 1)

index_path.write_text(index, encoding='utf-8')
endpoint_path.write_text(endpoint, encoding='utf-8')

built_index = index_path.read_text(encoding='utf-8')
built_endpoint = endpoint_path.read_text(encoding='utf-8')
for needle in [CARD_MARKER, MARKER, 'Storingen uit Excel importeren', 'Excel-sjabloon downloaden', 'faultExcelPlan', "action: 'import-faults'", 'Niet-destructieve import']:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: storings-Excel UI ontbreekt ({needle})')
for needle in [helper_marker, action_marker, 'faultImportKey', 'writeImportAudit', 'merged.push(fault)', 'saveConfig(store, { version: 1, faults: merged }']:
    if needle not in built_endpoint:
        raise SystemExit(f'Buildvalidatie mislukt: storings-Excel serverlogica ontbreekt ({needle})')

print('[Machinepark] Excel-import en sjabloon voor storingsbibliotheek onder Beheer actief')
