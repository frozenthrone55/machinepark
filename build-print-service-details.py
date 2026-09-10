from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="print-service-details-v2"'

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
    return lines.length ? lines.join(String.fromCharCode(10)) : (usedPartsText(parts) || '—');
  }}

  function serviceRecordPhotos(record) {{
    return Array.isArray(record?.photos)
      ? record.photos.filter(x => typeof x === 'string' && x.trim() && !window.machineparkIsVideoMedia?.(x)).slice(0,10)
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

  function serviceShouldUseIsolatedPrint() {{
    const ua = String(navigator.userAgent || '');
    const narrow = typeof window.matchMedia === 'function' && window.matchMedia('(max-width: 900px)').matches;
    const coarse = typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches;
    return narrow || coarse || /Android|iPhone|iPad|iPod|Mobile/i.test(ua);
  }}

  function serviceIsolatedPrintDocument(kind, record) {{
    const label = kind === 'maintenance' ? 'Onderhoud' : 'Depannage';
    const title = `Machinepark - ${{label}} - ${{serviceRecordDevice(record)}}`;
    const base = new URL('.', location.href).href;
    return `<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><base href="${{servicePrintEsc(base)}}"><title>${{servicePrintEsc(title)}}</title><style>
      @page{{margin:12mm}}
      html,body{{margin:0;background:#fff;color:#000;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif}}
      body{{padding:12mm;box-sizing:border-box}}
      .service-isolated-print-actions{{display:flex;justify-content:flex-end;margin:0 0 8mm}}
      .service-isolated-print-actions button{{font:inherit;padding:10px 16px;border:1px solid #777;border-radius:8px;background:#fff;color:#111}}
      .service-print-header{{display:flex;justify-content:space-between;align-items:flex-start;gap:18px;border-bottom:2px solid #222;padding-bottom:8mm;margin-bottom:7mm}}
      .service-print-header h1{{margin:0 0 2mm;font-size:20pt}}
      .service-print-subtitle{{font-size:10pt;color:#444}}
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
      @media(max-width:700px){{body{{padding:7mm}}.service-print-header{{gap:8px}}.service-print-grid{{grid-template-columns:1fr}}.service-print-field.full,.service-print-section{{grid-column:1}}}}
      @media print{{body{{padding:0}}.service-isolated-print-actions{{display:none!important}}}}
    </style></head><body><div class="service-isolated-print-actions"><button type="button" id="servicePrintNow">Afdrukken / PDF</button></div><main class="service-print-sheet">${{servicePrintHtml(kind, record)}}</main></body></html>`;
  }}

  function printServiceRecordIsolated(kind, record) {{
    const printWindow = window.open('', '_blank');
    if (!printWindow) return false;
    try {{
      printWindow.document.open();
      printWindow.document.write(serviceIsolatedPrintDocument(kind, record));
      printWindow.document.close();
      const manualButton = printWindow.document.getElementById('servicePrintNow');
      if (manualButton) manualButton.addEventListener('click', () => {{
        try {{ printWindow.focus(); printWindow.print(); }} catch (_) {{}}
      }});
      const images = [...printWindow.document.images];
      let printed = false;
      const triggerPrint = () => {{
        if (printed || printWindow.closed) return;
        printed = true;
        try {{ printWindow.focus(); printWindow.print(); }} catch (_) {{}}
      }};
      if (!images.length || images.every(img => img.complete)) {{
        setTimeout(triggerPrint, 80);
      }} else {{
        let pending = images.filter(img => !img.complete).length;
        const done = () => {{
          pending = Math.max(0, pending - 1);
          if (!pending) setTimeout(triggerPrint, 80);
        }};
        images.filter(img => !img.complete).forEach(img => {{
          img.addEventListener('load', done, {{ once: true }});
          img.addEventListener('error', done, {{ once: true }});
        }});
        setTimeout(triggerPrint, 1500);
      }}
      return true;
    }} catch (_) {{
      try {{ printWindow.close(); }} catch (_) {{}}
      return false;
    }}
  }}

  function printServiceRecord(kind, id) {{
    const list = kind === 'maintenance' ? state.maintenance : state.breakdowns;
    const record = list.find(x => x.id === id);
    if (!record) {{ toast('Verslag niet gevonden'); return; }}

    // Voorkom dat een mobiele/touch click na de detailafdruk nog de algemene
    // pagina-afdruk activeert. Die zou anders het Machinepark-overzicht openen.
    window.machineparkSuppressOverviewPrintUntil = Date.now() + 10000;

    // Op gsm staat de individuele werkzaamheid in een volledig zelfstandig
    // document. Daardoor kan de hoofdapp de reeds geopende PDF/printpreview
    // nooit meer vervangen door het actieve Machinepark-overzicht.
    if (serviceShouldUseIsolatedPrint() && printServiceRecordIsolated(kind, record)) return;

    const sheet = ensureServicePrintSheet();
    sheet.innerHTML = servicePrintHtml(kind, record);
    const oldTitle = document.title;
    const label = kind === 'maintenance' ? 'Onderhoud' : 'Depannage';
    document.title = `Machinepark - ${{label}} - ${{serviceRecordDevice(record)}}`;
    document.body.classList.add('service-record-printing');

    // Desktop en popup-blocker fallback: herstel pas als de echte printmodus
    // eindigt; nooit via een vaste korte timer.
    let restored = false;
    const printMedia = typeof window.matchMedia === 'function' ? window.matchMedia('print') : null;
    let printMediaStarted = Boolean(printMedia?.matches);
    let onPrintMediaChange = null;
    const restore = () => {{
      if (restored) return;
      restored = true;
      document.body.classList.remove('service-record-printing');
      document.title = oldTitle;
      window.removeEventListener('afterprint', restore);
      if (printMedia && onPrintMediaChange) {{
        if (typeof printMedia.removeEventListener === 'function') printMedia.removeEventListener('change', onPrintMediaChange);
        else if (typeof printMedia.removeListener === 'function') printMedia.removeListener(onPrintMediaChange);
      }}
    }};
    onPrintMediaChange = event => {{
      if (event.matches) {{
        printMediaStarted = true;
        return;
      }}
      if (printMediaStarted) restore();
    }};
    window.addEventListener('afterprint', restore);
    if (printMedia) {{
      if (typeof printMedia.addEventListener === 'function') printMedia.addEventListener('change', onPrintMediaChange);
      else if (typeof printMedia.addListener === 'function') printMedia.addListener(onPrintMediaChange);
    }}
    window.print();
  }}

  function addServicePrintButton(kind, id) {{
    const foot = document.querySelector('#modal .modal-foot');
    if (!foot || foot.querySelector('.service-detail-print-btn')) return;
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'btn service-detail-print-btn';
    btn.dataset.servicePrintKind = kind;
    btn.dataset.servicePrintId = id;
    btn.textContent = '🖨 Afdrukken';
    btn.addEventListener('click', event => {{
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      printServiceRecord(kind, id);
    }});
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
  window.machineparkServicePrintHtml = servicePrintHtml;
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
    "lines.join(String.fromCharCode(10))",
    "previousShowMaintenanceDetails",
    "previousOpenBreakdown",
    'btn.dataset.servicePrintKind = kind',
    'btn.dataset.servicePrintId = id',
    'window.machineparkServicePrintHtml = servicePrintHtml',
    "window.matchMedia('print')",
    "printMediaStarted",
    "printMedia.addEventListener('change', onPrintMediaChange)",
    "serviceShouldUseIsolatedPrint",
    "printServiceRecordIsolated",
    "window.open('', '_blank')",
    "machineparkSuppressOverviewPrintUntil",
    "event.stopImmediatePropagation()",
    "servicePrintNow",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: individuele verslagafdruk ontbreekt ({needle})")

obsolete_mobile_timeout = """setTimeout(() => {
      if (document.body.classList.contains('service-record-printing')) restore();
    }, 1800);"""
if obsolete_mobile_timeout in index:
    raise SystemExit("Buildvalidatie mislukt: individuele afdruk valt nog terug via vaste 1,8s timer")

print("[Machinepark] individuele onderhouds- en depannageverslagen afdrukbaar; gsm gebruikt geïsoleerd printdocument")
