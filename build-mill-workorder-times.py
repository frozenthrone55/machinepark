from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="mill-workorder-times-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    # Gebruik de bestaande machinedetailfunctie en voeg alleen een hook toe. Zo vermijden we
    # nog een extra wrapper rond showDeviceHistory.
    replace_once(
        "showModal('Machinedetails & logboek',body,'Sluiten',async()=>closeModal());setTimeout(()=>{const editDeviceBtn=$('#editDeviceFromHistory');",
        "showModal('Machinedetails & logboek',body,'Sluiten',async()=>closeModal());setTimeout(()=>window.machineparkInsertMillTimes?.(id),0);setTimeout(()=>{const editDeviceBtn=$('#editDeviceFromHistory');",
        'molentijdenhook in machinedetails',
    )

    style = f'''
<style {MARKER}>
.mill-latest-times-panel{{border:1px solid var(--line);border-radius:13px;background:#f8faf9;padding:13px}}
.mill-latest-times-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start;flex-wrap:wrap;margin-bottom:9px}}
.mill-latest-times-head strong{{font-size:13px}}
.mill-latest-times-head span{{font-size:10px;color:var(--muted)}}
.mill-latest-times-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}}
.mill-latest-time{{border:1px solid #e1e8e5;border-radius:10px;background:#fff;padding:9px;display:grid;gap:3px}}
.mill-latest-time span{{font-size:10px;color:var(--muted);font-weight:700}}
.mill-latest-time strong{{font-size:15px}}
.mill-latest-time small{{font-size:9px;color:var(--muted)}}
.workorder-last-value-hint{{font-size:10px;color:var(--muted);font-weight:600;margin-top:2px;opacity:.78}}
@media(max-width:760px){{.mill-latest-times-grid{{grid-template-columns:1fr 1fr}}}}
@media(max-width:480px){{.mill-latest-times-grid{{grid-template-columns:1fr}}}}
@media print{{
 .mill-latest-times-panel{{break-inside:avoid;background:#fff;border-color:#ccc}}
 .mill-latest-times-grid{{grid-template-columns:repeat(3,minmax(0,1fr));gap:2.5mm}}
 .mill-latest-time{{border-color:#ddd;padding:2.5mm}}
 .workorder-last-value-hint{{display:none!important}}
}}
</style>
'''

    script = r'''
<script data-machinepark-build-fix="mill-workorder-times-v1">
(() => {
  function millNorm(value) {
    return String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase().replace(/\s+/g, ' ');
  }

  function isMillWorkOrder(workOrder) {
    const name = millNorm(workOrder?.templateName || workOrder?.name || '');
    return name.includes('molen') || name.includes('grinder');
  }

  function isMillTimeField(field) {
    const label = millNorm(field?.label || '');
    if (!label) return false;
    return /\b(tijd|tijden|timer|time|seconde|seconden|second|seconds|duur)\b/.test(label)
      || /(^|\s)sec(?:\.|\s|$)/.test(label);
  }

  function millRecordSortKey(record) {
    const captured = String(record?.workOrder?.capturedAt || record?.updatedAt || record?.createdAt || '');
    const date = /^\d{4}-\d{2}-\d{2}$/.test(String(record?.date || ''))
      ? String(record.date)
      : captured.slice(0, 10);
    return `${date}|${captured}`;
  }

  function millRecordedDate(record) {
    const direct = String(record?.date || '');
    if (/^\d{4}-\d{2}-\d{2}$/.test(direct)) {
      try { return typeof dateFmt === 'function' ? dateFmt(direct) : direct; } catch (_) { return direct; }
    }
    const stamp = String(record?.workOrder?.capturedAt || record?.updatedAt || record?.createdAt || '');
    if (!stamp) return '—';
    const d = new Date(stamp);
    return Number.isNaN(d.getTime()) ? stamp.slice(0, 10) : d.toLocaleDateString('nl-BE');
  }

  function latestMillTimesForDevice(deviceId) {
    const records = (Array.isArray(state?.maintenance) ? state.maintenance : [])
      .filter((record) => record?.deviceId === deviceId && isMillWorkOrder(record?.workOrder))
      .sort((a, b) => millRecordSortKey(b).localeCompare(millRecordSortKey(a)));

    const byLabel = new Map();
    const byId = new Map();
    const entries = [];

    records.forEach((record) => {
      (Array.isArray(record?.workOrder?.fields) ? record.workOrder.fields : []).forEach((field) => {
        if (!isMillTimeField(field)) return;
        const value = String(field?.value ?? '').trim();
        if (!value) return;
        const labelKey = millNorm(field?.label || '');
        const idKey = String(field?.id || '').trim();
        if (!labelKey || byLabel.has(labelKey)) return;
        const entry = {
          id: idKey,
          label: String(field?.label || 'Tijd').trim(),
          labelKey,
          value,
          date: millRecordedDate(record),
          sortKey: millRecordSortKey(record),
          maintenanceId: String(record?.id || ''),
        };
        byLabel.set(labelKey, entry);
        if (idKey && !byId.has(idKey)) byId.set(idKey, entry);
        entries.push(entry);
      });
    });

    return { entries, byLabel, byId };
  }
  window.machineparkLatestMillTimesForDevice = latestMillTimesForDevice;

  function deviceIdForWorkOrderEditor(editor) {
    const card = editor?.closest('.maintenance-machine-card');
    if (card?.dataset?.maintenanceDevice) return card.dataset.maintenanceDevice;
    const modal = editor?.closest('#modal') || document.querySelector('#modal');
    return String(modal?.querySelector('[name="deviceId"]')?.value || '');
  }

  function selectedWorkOrderLooksLikeMill(editor) {
    const select = editor?.querySelector('.workorder-maintenance-select');
    if (!select || !select.value || select.value === '__saved__') return false;
    const text = millNorm(select.selectedOptions?.[0]?.textContent || '');
    return text.includes('molen') || text.includes('grinder');
  }

  function clearMillHints(editor) {
    editor?.querySelectorAll('.workorder-last-value-hint').forEach((node) => node.remove());
  }

  function annotateMillWorkOrderEditor(editor) {
    if (!editor) return;
    clearMillHints(editor);
    if (!selectedWorkOrderLooksLikeMill(editor)) return;
    const deviceId = deviceIdForWorkOrderEditor(editor);
    if (!deviceId) return;
    const latest = latestMillTimesForDevice(deviceId);
    if (!latest.entries.length) return;

    editor.querySelectorAll('.workorder-maintenance-field').forEach((fieldBox) => {
      const input = fieldBox.querySelector('[data-workorder-field]');
      const labelNode = fieldBox.querySelector('label');
      if (!input || !labelNode) return;
      const label = String(labelNode.textContent || '').replace(/\s*\*\s*$/, '').trim();
      if (!isMillTimeField({ label })) return;
      const id = String(input.dataset.workorderField || '');
      const previous = (id && latest.byId.get(id)) || latest.byLabel.get(millNorm(label));
      if (!previous) return;
      const hint = document.createElement('div');
      hint.className = 'workorder-last-value-hint';
      hint.textContent = `Vorige waarde: ${previous.value} · ${previous.date}`;
      fieldBox.appendChild(hint);
    });
  }

  let hintFrame = 0;
  function annotateVisibleMillWorkOrders() {
    if (hintFrame) cancelAnimationFrame(hintFrame);
    hintFrame = requestAnimationFrame(() => {
      hintFrame = 0;
      document.querySelectorAll('#modal [data-workorder-editor]').forEach(annotateMillWorkOrderEditor);
    });
  }

  document.addEventListener('change', (event) => {
    if (event.target?.classList?.contains('workorder-maintenance-select')) setTimeout(annotateVisibleMillWorkOrders, 0);
  });

  const modalRoot = document.getElementById('modalBackdrop') || document.body;
  const observer = new MutationObserver(() => annotateVisibleMillWorkOrders());
  observer.observe(modalRoot, { childList: true, subtree: true });

  function millLatestTimesHtml(deviceId) {
    const latest = latestMillTimesForDevice(deviceId);
    if (!latest.entries.length) return '';
    const rows = latest.entries
      .sort((a, b) => a.label.localeCompare(b.label, 'nl-BE', { numeric: true, sensitivity: 'base' }))
      .map((entry) => `<div class="mill-latest-time"><span>${esc(entry.label)}</span><strong>${esc(entry.value)}</strong><small>Laatst genoteerd op ${esc(entry.date)}</small></div>`)
      .join('');
    return `<div class="mill-latest-times-panel"><div class="mill-latest-times-head"><strong>Laatste molentijden</strong><span>Steeds de recentste ingevulde waarde per tijdsveld</span></div><div class="mill-latest-times-grid">${rows}</div></div>`;
  }
  window.machineparkMillLatestTimesHtml = millLatestTimesHtml;

  window.machineparkInsertMillTimes = function(id) {
    const html = millLatestTimesHtml(id);
    if (!html) return;
    const grid = document.querySelector('#modal .modal-body .form-grid');
    if (!grid || grid.querySelector('.mill-latest-times-block')) return;
    const block = document.createElement('div');
    block.className = 'field full mill-latest-times-block';
    block.innerHTML = html;
    const history = [...grid.children].find((node) => node.querySelector?.('.history-group'));
    if (history) grid.insertBefore(block, history);
    else grid.appendChild(block);
  };
})();
</script>
'''

    pos = index.rfind('</body>')
    if pos < 0:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor molentijden')
    index = index[:pos] + style + script + index[pos:]
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'latestMillTimesForDevice',
    'Laatste molentijden',
    'Vorige waarde:',
    'Laatst genoteerd op',
    "name.includes('molen')",
    'workorder-last-value-hint',
    'mill-latest-times-panel',
    'machineparkInsertMillTimes',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: molentijdenfunctie ontbreekt ({needle})')

print('[Machinepark] laatste molentijden zichtbaar in machinedetails en als referentie in nieuwe werkbonnen')
