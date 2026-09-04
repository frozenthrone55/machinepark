from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="unified-work-layout-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    start = index.find("  function servicePrintHtml(kind, record) {")
    end = index.find("\n\n  function ensureServicePrintSheet()", start)
    if start < 0 or end < 0:
        raise SystemExit("Buildvalidatie mislukt: individuele werkverslag-afdrukfunctie niet gevonden")

    print_renderer = r'''  function unifiedWorkPartRows(record) {
    const rows = [];
    (record?.usedParts || []).forEach(usage => {
      const qty = Number(usage?.qty || 0);
      if (!usage?.partId || qty <= 0) return;
      const part = (state.parts || []).find(item => item.id === usage.partId);
      rows.push({
        code:String(part?.artNr || usage.partId || '—').trim() || '—',
        description:String(part?.description || '').trim(),
        qty,
        oneOff:false
      });
    });
    (record?.oneOffParts || []).forEach(part => {
      const supplier = String(part?.supplier || '').trim();
      const supplierCode = String(part?.supplierCode || '').trim();
      const description = String(part?.description || '').trim();
      if (!(supplier || supplierCode || description)) return;
      rows.push({
        code:supplierCode || supplier || 'Eenmalig',
        description:[supplierCode && supplier ? supplier : '', description].filter(Boolean).join(' · '),
        qty:Math.max(1, Math.round(Number(part?.qty) || 1)),
        oneOff:true
      });
    });
    return rows;
  }

  function unifiedWorkLocation(record) {
    const device = (state.devices || []).find(item => item.id === record?.deviceId);
    try {
      if (device && typeof deviceLocationAt === 'function') return deviceLocationAt(device, recordMoment(record)) || device.location || '—';
    } catch (_) {}
    return device?.location || record?.serviceVisitLocation || '—';
  }

  function unifiedWorkSummary(kind, record) {
    try {
      if (kind === 'maintenance' && typeof maintenanceWorkSummary === 'function') return maintenanceWorkSummary(record);
      if (typeof breakdownWorkSummary === 'function') return breakdownWorkSummary(record);
    } catch (_) {}
    const sessions = Array.isArray(record?.workSessions) ? record.workSessions : [];
    const minutes = sessions.reduce((sum, row) => sum + Math.max(0, Math.round(Number(row?.minutes) || 0)), 0) || Math.max(0, Math.round(Number(record?.hours || 0) * 60));
    const count = Math.max(1, Math.round(Number(record?.serviceReportDeviceCount || record?.serviceVisitDeviceCount || record?.batchSize) || 1));
    return `${minutes} min / ${count} toestel${count === 1 ? '' : 'len'}`;
  }

  function unifiedWorkPartsHtml(record) {
    const rows = unifiedWorkPartRows(record);
    return `<div class="work-report-parts-box"><div class="work-report-parts-title">Onderdelen voor deze werkzaamheid</div>${rows.length ? `<table class="work-report-parts-table"><thead><tr><th class="work-part-code">Onderdeel</th><th class="work-part-description">Omschrijving</th><th class="work-part-qty">Aantal</th></tr></thead><tbody>${rows.map(row => `<tr><td class="work-part-code">${servicePrintEsc(row.code || '—')}</td><td class="work-part-description">${servicePrintEsc(row.description || '—')}${row.oneOff ? '<small>Eenmalig / leverancier</small>' : ''}</td><td class="work-part-qty"><strong>${servicePrintEsc(row.qty)}</strong></td></tr>`).join('')}</tbody></table>` : '<div class="work-report-parts-empty">Geen onderdelen gebruikt.</div>'}</div>`;
  }

  function servicePrintHtml(kind, record) {
    const maintenance = kind === 'maintenance';
    const other = !maintenance && record?.serviceKind === 'other';
    const kindLabel = maintenance ? 'Onderhoud' : (other ? (record.workTypeName || 'Andere werken') : 'Depannage');
    const title = maintenance ? 'Onderhoudsverslag' : (other ? `${kindLabel} · verslag` : 'Depannageverslag');
    const device = serviceRecordDevice(record);
    const date = serviceRecordDate(record);
    const summary = unifiedWorkSummary(kind, record);
    const summaryLabel = record?.serviceVisitId ? 'Servicetijd volledig verslag / toestellen' : 'Datum / werkminuten';
    const summaryValue = record?.serviceVisitId ? summary : `${date} · ${summary}`;
    const details = maintenance
      ? [
          `Type onderhoud: ${record.type || '—'}`,
          `Uitgevoerde werkzaamheden / notitie: ${record.notes || '—'}`
        ]
      : other
        ? [
            `Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`,
            `Werkzaamheid / omschrijving: ${record.issue || '—'}`,
            `Extra info / diagnose: ${record.diagnosis || '—'}`,
            `Oplossing / uitgevoerde werken: ${record.solution || '—'}`
          ]
        : [
            `Prioriteit: ${record.priority || '—'} · Status: ${record.status || '—'}`,
            `Probleem / melding: ${record.issue || '—'}`,
            `Diagnose: ${record.diagnosis || '—'}`,
            `Oplossing / uitgevoerde werken: ${record.solution || '—'}`
          ];
    const photos = serviceRecordPhotos(record);
    return `<section class="work-report-print-page">
      <div class="work-report-print-head"><div><small>WERKVERSLAG</small><strong>${servicePrintEsc(title)}</strong></div><div class="work-report-print-kind">${servicePrintEsc(kindLabel)}</div></div>
      <div class="work-report-print-title"><h1>${servicePrintEsc(device)}</h1></div>
      <div class="work-report-print-meta">
        <div><small>Locatie</small><strong>${servicePrintEsc(unifiedWorkLocation(record))}</strong></div>
        <div><small>${servicePrintEsc(summaryLabel)}</small><strong>${servicePrintEsc(summaryValue)}</strong></div>
        <div><small>Technieker</small><strong>${servicePrintEsc(record.technician || '—')}</strong></div>
      </div>
      <div class="work-report-print-card">
        <div class="work-report-print-lines">${details.map(line => `<div>${servicePrintEsc(line)}</div>`).join('')}</div>
        ${unifiedWorkPartsHtml(record)}
      </div>
      ${photos.length ? `<div class="work-report-print-photos"><div class="work-report-section-title">Foto’s bij deze werkzaamheid</div><div class="service-print-photo-grid">${photos.map((src, index) => `<div class="service-print-photo"><img src="${src}" alt="Verslagfoto ${index + 1}"></div>`).join('')}</div></div>` : ''}
    </section>`;
  }'''

    index = index[:start] + print_renderer + index[end:]

    style = rf'''
<style {MARKER}>
.work-overview-panel{{margin:0 0 14px;border:1px solid var(--line);border-radius:14px;background:var(--panel,#fff);overflow:hidden}}
.work-overview-panel>.service-visit-panel-head{{padding:12px 14px;background:#fff}}
.work-overview-panel>.service-visit-panel-head h3{{margin:0;font-size:15px}}
.work-overview-panel>.service-visit-panel-head p{{margin:3px 0 0;font-size:11px;color:var(--muted)}}
.work-overview-panel .work-overview-table-wrap{{border:0!important;border-radius:0!important;margin:0!important;box-shadow:none!important}}
.work-overview-panel .table thead th{{background:#f4f7f5;color:#45574f;font-size:10px;font-weight:850;text-transform:uppercase;letter-spacing:.025em;border-bottom:1px solid #cfd8d4}}
.work-overview-panel .table tbody td{{vertical-align:top;border-bottom:1px solid #e2e8e5}}
.work-overview-panel .table tbody tr:last-child td{{border-bottom:0}}
.work-overview-panel .table tbody tr:hover{{background:#f8faf9}}
.work-overview-panel .btn.small{{border-radius:8px}}
.work-overview-panel .badge{{font-weight:850}}
.work-report-print-page{{display:block}}
.work-report-print-head{{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;border-bottom:2px solid #183f35;padding-bottom:8px}}
.work-report-print-head small{{display:block;font-size:10px;font-weight:850;text-transform:uppercase;margin-bottom:3px}}
.work-report-print-head strong{{display:block;font-size:13px}}
.work-report-print-kind{{background:#183f35;color:#fff;border-radius:999px;padding:7px 14px;font-size:12px;font-weight:900}}
.work-report-print-title h1{{margin:14px 0 10px;font-size:21px}}
.work-report-print-meta{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-bottom:5mm}}
.work-report-print-meta>div{{border:1.4px solid #555;border-radius:10px;padding:9px;background:#ececea}}
.work-report-print-meta small{{display:block;color:#333;font-size:10px;font-weight:850;text-transform:uppercase;margin-bottom:3px}}
.work-report-print-meta strong{{display:block;color:#111;font-size:12px}}
.work-report-print-card{{border:1.4px solid #555;border-radius:12px;padding:12px;color:#111}}
.work-report-print-lines{{display:grid;gap:7px;font-size:12px;line-height:1.45}}
.work-report-parts-box{{margin-top:12px;border:1.4px solid #555;border-radius:10px;overflow:hidden;background:#fff}}
.work-report-parts-title{{padding:8px 10px;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.035em;background:#dededb;border-bottom:1.4px solid #555}}
.work-report-parts-table{{width:100%;border-collapse:collapse;font-size:12px}}
.work-report-parts-table th,.work-report-parts-table td{{padding:8px 10px;text-align:left;vertical-align:top;border-bottom:1px solid #888}}
.work-report-parts-table tr:last-child td{{border-bottom:0}}
.work-report-parts-table th{{font-size:10px;text-transform:uppercase;color:#111;font-weight:900;background:#ececea}}
.work-report-parts-table .work-part-code{{width:1%;white-space:nowrap;padding-right:calc(3ch + 10px)}}
.work-report-parts-table .work-part-description{{width:auto;white-space:normal;overflow-wrap:anywhere}}
.work-report-parts-table .work-part-qty{{width:74px;text-align:right;white-space:nowrap}}
.work-report-parts-table td small{{display:block;margin-top:2px;color:#333;font-size:9px;font-weight:700;text-transform:uppercase}}
.work-report-parts-empty{{padding:10px;font-size:12px;color:#333}}
.work-report-print-photos{{margin-top:6mm}}
.work-report-section-title{{font-size:11px;font-weight:900;text-transform:uppercase;border-bottom:1px solid #555;padding-bottom:4px;margin-bottom:8px}}
@media print{{
  body.service-record-printing .service-print-sheet{{display:block!important}}
  .service-print-sheet{{color:#111!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .service-print-sheet>.work-report-print-page{{display:block!important}}
  .service-print-header,.service-print-grid,.service-print-footer{{display:none!important}}
  .work-report-print-head,.work-report-print-meta>div,.work-report-print-card,.work-report-parts-box,.work-report-parts-table th,.work-report-parts-table td{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  .work-report-print-card,.work-report-parts-box,.service-print-photo{{break-inside:avoid}}
  .work-report-print-kind{{background:#183f35!important;color:#fff!important}}
  .work-overview-panel{{border-color:#555!important;box-shadow:none!important}}
  .work-overview-panel>.service-visit-panel-head{{background:#fff!important;border-bottom:1.4px solid #555!important}}
  .work-overview-panel .table thead th{{background:#dededb!important;color:#111!important;border-bottom:1.4px solid #555!important}}
  .work-overview-panel .table tbody td{{color:#111!important;border-bottom:1px solid #888!important}}
}}
</style>
'''

    runtime = rf'''
<script {MARKER}>
(() => {{
  const definitions = [
    ['view-maintenance','Onderhoudsverslagen','Overzicht van geregistreerd onderhoud per toestel.'],
    ['view-breakdowns','Depannageverslagen','Overzicht van geregistreerde depannages per toestel.'],
    ['view-otherworks','Andere werken','Plaatsingen en andere werkzaamheden per toestel.'],
    ['view-work','Werkzaamhedenoverzicht','Onderhoud, depannages en andere werken in één overzicht.']
  ];

  function ensurePageActions(view, title) {{
    if (!view || view.querySelector(':scope > .page-print-row')) return;
    const row = document.createElement('div');
    row.className = 'page-print-row';
    row.innerHTML = `<div class="page-print-heading">Machinepark · ${title}</div><button type="button" class="btn page-print-btn">🖨 Afdrukken</button><button type="button" class="btn page-mail-btn">✉ Mail PDF</button>`;
    row.querySelector('.page-print-btn')?.addEventListener('click', () => window.printMachineparkView?.(view));
    view.insertAdjacentElement('afterbegin', row);
  }}

  function decorateOverview(id, title, description) {{
    const view = document.getElementById(id);
    if (!view) return;
    ensurePageActions(view, title);
    if (view.querySelector(':scope > .work-overview-panel')) return;
    const wrap = view.querySelector('.table-wrap');
    if (!wrap || !wrap.parentNode) return;
    const panel = document.createElement('div');
    panel.className = 'work-overview-panel service-visit-panel';
    panel.innerHTML = `<div class="service-visit-panel-head"><div><h3>${title}</h3><p>${description}</p></div></div>`;
    wrap.parentNode.insertBefore(panel, wrap);
    wrap.classList.add('work-overview-table-wrap');
    panel.appendChild(wrap);
  }}

  function apply() {{ definitions.forEach(args => decorateOverview(...args)); }}
  apply();
  setTimeout(apply, 0);
  setTimeout(apply, 250);
  window.machineparkApplyUnifiedWorkLayout = apply;
}})();
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor uniforme werkverslagen")
    index = index.replace("</head>", style + "</head>", 1)
    index = index.replace("</body>", runtime + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "function unifiedWorkPartRows",
    "function unifiedWorkPartsHtml",
    "function unifiedWorkLocation",
    "function unifiedWorkSummary",
    "Servicetijd volledig verslag / toestellen",
    "Datum / werkminuten",
    "Onderdelen voor deze werkzaamheid",
    "work-report-parts-table",
    "work-part-code",
    "padding-right:calc(3ch + 10px)",
    "work-overview-panel",
    "Onderhoudsverslagen",
    "Depannageverslagen",
    "Werkzaamhedenoverzicht",
    "page-mail-btn",
    "machineparkApplyUnifiedWorkLayout",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: uniforme werkverslagen ontbreken ({needle})")

print("[Machinepark] onderhoud, depannage en andere werken volgen dezelfde overzicht- en afdruklayout als Service")
