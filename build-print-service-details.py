from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="print-service-details-v1"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
.service-detail-print-btn{{display:inline-flex;align-items:center;gap:7px}}
.service-print-sheet{{display:none}}
@media print{{
  body.service-record-printing .app,
  body.service-record-printing .modal-backdrop,
  body.service-record-printing .toast{{display:none!important}}
  body.service-record-printing .service-print-sheet{{display:block!important}}
  body.service-record-printing{{background:#fff!important;color:#000!important}}
  .service-print-sheet{{font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#000}}
  .service-print-header{{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;border-bottom:2px solid #222;padding-bottom:8mm;margin-bottom:7mm}}
  .service-print-header h1{{margin:0 0 2mm;font-size:20pt}}
  .service-print-header .service-print-subtitle{{font-size:10pt;color:#444}}
  .service-print-grid{{display:grid;grid-template-columns:1fr 1fr;gap:5mm 8mm}}
  .service-print-field{{break-inside:avoid}}
  .service-print-field.full{{grid-column:1/-1}}
  .service-print-label{{font-size:8.5pt;font-weight:800;text-transform:uppercase;letter-spacing:.04em;color:#555;margin-bottom:1.5mm}}
  .service-print-value{{font-size:10.5pt;line-height:1.45;white-space:pre-wrap}}
  .service-print-section{{grid-column:1/-1;border-top:1px solid #bbb;padding-top:5mm;margin-top:1mm}}
  .service-print-section h2{{font-size:12pt;margin:0 0 3mm}}
  .service-print-photo-grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:5mm}}
  .service-print-photo{{break-inside:avoid;border:1px solid #bbb;padding:2mm}}
  .service-print-photo img{{display:block;width:100%;max-height:105mm;object-fit:contain}}
  .service-print-footer{{margin-top:10mm;padding-top:4mm;border-top:1px solid #bbb;font-size:8.5pt;color:#555}}
}}
</style>
'''

    script = f'''
<script {MARKER}>
(() => {{
  function servicePrintEsc(value) {{
    return esc(String(value ?? ''));
  }}

  function serviceRecordDevice(record) {{
    return deviceName(record.deviceId, recordMoment(record));
  }}

  function serviceRecordDate(record) {{
    if (!record?.date) return '—';
    const date = new Date(`${{record.date}}T00:00:00`);
    return Number.isNaN(date.getTime()) ? String(record.date) : date.toLocaleDateString('nl-BE');
  }}

  function serviceRecordParts(record, multiline = false) {{
    const parts = Array.isArray(record?.usedParts) ? record.usedParts.filter(Boolean) : [];
    if (!parts.length) return '—';
    if (!multiline) return usedPartsText(parts) || '—';
    const lines = parts
      .map(part => usedPartsText([part]))
      .map(value => String(value || '').trim())
      .filter(Boolean);
    return lines.length ? lines.join('\n') : (usedPartsText(parts) || '—');
  }}

  function serviceRecordPhotos(record) {{
    return Array.isArray(record?.photos)
      ? record.photos.filter(x => typeof x === 'string' && x.startsWith('data:image/'))
      : [];
  }}

  function servicePrintField(label, value, full = false) {{
    return `<div class="service-print-field${{full ? ' full' : ''}}"><div class="service-print-label">${{servicePrintEsc(label)}}</div><div class="service-print-value">${{servicePrintEsc(value || '—')}}</div></div>`;
  }}

  function servicePrintPhotos(record) {{
    const photos = serviceRecordPhotos(record);
    if (!photos.length) return '';
    return `<div class="service-print-section"><h2>Foto’s bij verslag</h2><div class="service-print-photo-grid">${{photos.map((src, index) => `<div class="service-print-photo"><img src="${{src}}" alt="Verslagfoto ${{index + 1}}"></div>`).join('')}}</div></div>`;
  }}

  function servicePrintHtml(kind, record) {{
    const isMaintenance = kind === 'maintenance';
    const title = isMaintenance ? 'Onderhoudsverslag' : 'Depannageverslag';
    const fields = isMaintenance
      ? [
          servicePrintField('Datum', serviceRecordDate(record)),
          servicePrintField('Type onderhoud', record.type || '—'),
          servicePrintField('Toestel', serviceRecordDevice(record), true),
          servicePrintField('Technieker', record.technician || '—'),
          servicePrintField('Gebruikte onderdelen', serviceRecordParts(record), true),
          servicePrintField('Uitgevoerde werkzaamheden / notitie', record.notes || '—', true),
        ].join('')
      : [
          servicePrintField('Datum', serviceRecordDate(record)),
          servicePrintField('Toestel', serviceRecordDevice(record)),
          servicePrintField('Prioriteit', record.priority || '—'),
          servicePrintField('Status', record.status || '—'),
          servicePrintField('Technieker', record.technician || '—'),
          servicePrintField('Werkuren', Number(record.hours || 0) ? `${{Number(record.hours)}} uur` : '—'),
          servicePrintField('Probleem / melding', record.issue || '—', true),
          servicePrintField('Diagnose', record.diagnosis || '—', true),
          servicePrintField('Oplossing / uitgevoerde werken', record.solution || '—', true),
          servicePrintField('Gebruikte onderdelen', serviceRecordParts(record, true), true),
        ].join('');

    return `<div class="service-print-header"><div><h1>Machinepark · ${{title}}</h1><div class="service-print-subtitle">${{servicePrintEsc(serviceRecordDevice(record))}}</div></div><div class="service-print-subtitle">${{servicePrintEsc(serviceRecordDate(record))}}</div></div><div class="service-print-grid">${{fields}}${{servicePrintPhotos(record)}}</div><div class="service-print-footer">Afgedrukt vanuit Machinepark</div>`;
  }}

  function ensureServicePrintSheet() {{
    let sheet = document.getElementById('servicePrintSheet');
    if (!sheet) {{
      sheet = document.createElement('div');
      sheet.id = 'servicePrintSheet';
      sheet.className = 'service-print-sheet';
      document.body.appendChild(sheet);
    }}
    return sheet;
  }}

  function printServiceRecord(kind, id) {{
    const list = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    const record = list.find(x => x.id === id);
    if (!record) {{ toast('Verslag niet gevonden'); return; }}
    const sheet = ensureServicePrintSheet();
    sheet.innerHTML = servicePrintHtml(kind, record);
    const oldTitle = document.title;
    const label = kind === 'maintenance' ? 'Onderhoud' : 'Depannage';
    document.title = `Machinepark - ${{label}} - ${{serviceRecordDevice(record)}}`;
    document.body.classList.add('service-record-printing');
    const restore = () => {{
      document.body.classList.remove('service-record-printing');
      document.title = oldTitle;
      window.removeEventListener('afterprint', restore);
    }};
    window.addEventListener('afterprint', restore);
    window.print();
    setTimeout(() => {{
      if (document.body.classList.contains('service-record-printing')) restore();
    }}, 1800);
  }}

  function addServicePrintButton(kind, id) {{
    const foot = document.querySelector('#modal .modal-foot');
    if (!foot || foot.querySelector('.service-detail-print-btn')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn service-detail-print-btn';
    btn.textContent = '🖨 Afdrukken';
    btn.onclick = () => printServiceRecord(kind, id);
    foot.insertBefore(btn, foot.querySelector('.btn.primary') || null);
  }}

  const previousShowMaintenanceDetails = showMaintenanceDetails;
  showMaintenanceDetails = function(id) {{
    const result = previousShowMaintenanceDetails(id);
    setTimeout(() => addServicePrintButton('maintenance', id), 0);
    return result;
  }};

  const previousOpenBreakdown = openBreakdown;
  openBreakdown = function(id) {{
    const result = previousOpenBreakdown(id);
    if (id) setTimeout(() => addServicePrintButton('breakdowns', id), 0);
    return result;
  }};

  window.printMachineparkServiceRecord = printServiceRecord;
}})();
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor individuele verslagafdruk")
    index = index.replace("</head>", style + "</head>", 1)
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "service-detail-print-btn",
    "printServiceRecord",
    "Onderhoudsverslag",
    "Depannageverslag",
    "Foto’s bij verslag",
    "servicePrintField('Datum'",
    "serviceRecordDate",
    "serviceRecordParts(record, true)",
    "lines.join('\\n')",
    "previousShowMaintenanceDetails",
    "previousOpenBreakdown",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: individuele verslagafdruk ontbreekt ({needle})")

print("[Machinepark] individuele onderhouds- en depannageverslagen afdrukbaar zonder uur")
