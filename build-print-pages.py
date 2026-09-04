from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="print-every-page-v2"'

if MARKER not in index:
    style = f'''
<style {MARKER}>
.page-print-row{{display:flex;justify-content:flex-end;align-items:center;margin:-5px 0 16px}}
.page-print-row .page-print-heading{{display:none}}
.page-print-btn{{display:inline-flex;align-items:center;gap:7px}}
@media(max-width:700px){{
  .page-print-row{{margin:0 0 14px}}
  .page-print-btn{{width:100%;justify-content:center}}
}}
@media print{{
  @page{{margin:12mm}}
  html,body{{background:#fff!important;color:#000!important}}
  body{{font-size:10pt}}
  .sidebar,.topbar,.toast,.modal-backdrop{{display:none!important}}
  .app{{display:block!important;min-height:0!important}}
  .main{{padding:0!important;min-width:0!important}}
  .view{{display:none!important}}
  .view.active{{display:block!important}}
  .page-print-row{{display:block!important;margin:0 0 8mm!important;border-bottom:1px solid #bbb;padding-bottom:4mm}}
  .page-print-row .page-print-heading{{display:block!important;font-size:20pt;font-weight:800;color:#000!important}}
  .page-print-btn{{display:none!important}}
  .toolbar{{display:none!important}}
  .panel-head button,.settings-card button,.settings-card form,.settings-card input[type=file]{{display:none!important}}
  .panel,.kpi,.device-card,.settings-card,.table-wrap{{box-shadow:none!important}}
  .panel,.kpi,.device-card,.settings-card{{break-inside:avoid}}
  .table-wrap{{overflow:visible!important;border-color:#bbb!important}}
  .table,.device-table{{width:100%!important;min-width:0!important;table-layout:auto!important}}
  .table th,.table td{{font-size:8.5pt!important;padding:6px 7px!important;color:#000!important}}
  .table th{{position:static!important;background:#f1f1f1!important;print-color-adjust:exact;-webkit-print-color-adjust:exact}}
  .kpis{{grid-template-columns:repeat(4,1fr)!important;gap:8px!important}}
  .grid2{{grid-template-columns:1.45fr 1fr!important;gap:10px!important}}
  #view-parts img.thumb.parts-print-photo{{max-width:none!important;max-height:none!important;object-fit:contain!important}}
  a{{color:#000!important;text-decoration:none!important}}
}}
</style>
'''

    script = f'''
<script {MARKER}>
(() => {{
  const labels = {{
    dashboard: 'Dashboard',
    devices: 'Toestellen',
    maintenance: 'Onderhoud',
    breakdowns: 'Depannages',
    parts: 'Onderdelen',
    settings: 'Beheer'
  }};

  function viewName(view) {{
    const key = String(view?.id || '').replace(/^view-/, '');
    return labels[key] || document.getElementById('pageTitle')?.textContent?.trim() || 'Machinepark';
  }}

  function addPrintButton(view) {{
    if (!view || view.querySelector(':scope > .page-print-row')) return;
    const row = document.createElement('div');
    row.className = 'page-print-row';
    row.innerHTML = `<div class="page-print-heading">Machinepark · ${{viewName(view)}}</div><button type="button" class="btn page-print-btn" aria-label="Deze pagina afdrukken">🖨 Afdrukken</button>`;
    row.querySelector('.page-print-btn').addEventListener('click', () => printMachineparkView(view));
    view.insertAdjacentElement('afterbegin', row);
  }}

  function activeView() {{
    return document.querySelector('.view.active') || document.querySelector('.view');
  }}

  function enlargePartsPrintPhotos(view) {{
    if (view?.id !== 'view-parts') return () => {{}};
    const photos = [...view.querySelectorAll('img.thumb')];
    const original = photos.map(img => ({{
      img,
      width: img.style.width,
      height: img.style.height,
    }}));
    photos.forEach(img => {{
      const rect = img.getBoundingClientRect();
      if (rect.width > 0) img.style.width = `${{Math.round(rect.width * 1.5)}}px`;
      if (rect.height > 0) img.style.height = `${{Math.round(rect.height * 1.5)}}px`;
      img.classList.add('parts-print-photo');
    }});
    return () => original.forEach(({{img,width,height}}) => {{
      img.style.width = width;
      img.style.height = height;
      img.classList.remove('parts-print-photo');
    }});
  }}

  function printMachineparkView(view = activeView()) {{
    if (!view) return;
    const name = viewName(view);
    const heading = view.querySelector(':scope > .page-print-row .page-print-heading');
    if (heading) heading.textContent = `Machinepark · ${{name}}`;
    const restorePhotos = enlargePartsPrintPhotos(view);
    const oldTitle = document.title;
    document.title = `Machinepark - ${{name}}`;
    let restored = false;
    const restore = () => {{
      if (restored) return;
      restored = true;
      restorePhotos();
      document.title = oldTitle;
      window.removeEventListener('afterprint', restore);
    }};
    window.addEventListener('afterprint', restore);
    window.print();
    setTimeout(restore, 1800);
  }}

  window.printMachineparkView = printMachineparkView;
  document.querySelectorAll('.view').forEach(addPrintButton);
}})();
</script>
'''

    if "</head>" not in index or "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-afsluiters ontbreken voor afdrukoptie")
    index = index.replace("</head>", style + "</head>", 1)
    index = index.replace("</body>", script + "</body>", 1)
    index_path.write_text(index, encoding="utf-8")

required = [
    MARKER,
    "page-print-btn",
    "printMachineparkView",
    "window.print()",
    "enlargePartsPrintPhotos",
    "Math.round(rect.width * 1.5)",
    "Math.round(rect.height * 1.5)",
    "parts-print-photo",
    "dashboard: 'Dashboard'",
    "devices: 'Toestellen'",
    "maintenance: 'Onderhoud'",
    "breakdowns: 'Depannages'",
    "parts: 'Onderdelen'",
    "settings: 'Beheer'",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Buildvalidatie mislukt: afdrukfunctie ontbreekt ({needle})")

print("[Machinepark] afdrukoptie op elke pagina actief; onderdeelafbeeldingen 50% groter op print")
