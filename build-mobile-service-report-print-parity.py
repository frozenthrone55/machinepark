from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
js_path = ROOT / 'service-visits.js'
js = js_path.read_text(encoding='utf-8')
MARKER = 'machinepark-mobile-service-report-print-parity-v1'

if MARKER not in js:
    start = js.find('  function serviceReportPrintStylesheet() {')
    end = js.find('  function printServiceReportIsolated(report) {', start)
    if start < 0 or end < 0:
        raise SystemExit('Buildvalidatie mislukt: mobiele serviceverslag-printbasis niet gevonden voor layoutpariteit')

    replacement = r'''  function serviceReportPrintHeadStyles() {
    // machinepark-mobile-service-report-print-parity-v1
    // Kopieer exact dezelfde CSS-bronnen als de hoofdapp. Zo gebruikt de
    // geïsoleerde gsm-afdruk dezelfde algemene én serviceverslag-printregels als pc.
    return [...document.querySelectorAll('style,link[rel="stylesheet"]')].map(node=>{
      if(node.tagName==='STYLE')return `<style>${node.textContent||''}</style>`;
      const href=String(node.href||node.getAttribute('href')||'').trim();
      if(!href)return '';
      const media=String(node.media||'').trim();
      return `<link rel="stylesheet" href="${svEsc(href)}"${media?` media="${svEsc(media)}"`:''}>`;
    }).join('');
  }

  function serviceReportIsolatedPrintDocument(report) {
    const title=`Machinepark - Serviceverslag - ${reportDisplayLabel(report)}`;
    const styles=serviceReportPrintHeadStyles();
    return `<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${svEsc(title)}</title>${styles}<style>
      /* Alleen de tijdelijke bediening is specifiek voor het losse gsm-document.
         De serviceverslag-layout zelf komt volledig uit dezelfde CSS als op pc. */
      .service-visit-print-sheet{display:block!important}
      .service-report-isolated-actions{display:flex;justify-content:flex-end;margin:12px 12px 18px}
      .service-report-isolated-actions button{font:inherit;padding:10px 16px;border:1px solid var(--line,#777);border-radius:8px;background:#fff;color:var(--text,#111)}
      @media print{.service-report-isolated-actions{display:none!important}.service-visit-print-sheet{display:block!important}}
    </style></head><body class="service-visit-printing"><div class="service-report-isolated-actions"><button type="button" id="serviceReportPrintNow">Afdrukken / PDF</button></div><main class="service-visit-print-sheet">${reportHtml(report)}</main></body></html>`;
  }

'''
    js = js[:start] + replacement + js[end:]
    js_path.write_text(js, encoding='utf-8')

built = js_path.read_text(encoding='utf-8')
required = [
    MARKER,
    'serviceReportPrintHeadStyles',
    "document.querySelectorAll('style,link[rel=\"stylesheet\"]')",
    "if(node.tagName==='STYLE')",
    "const href=String(node.href||node.getAttribute('href')||'').trim()",
    '<body class="service-visit-printing">',
    '<main class="service-visit-print-sheet">${reportHtml(report)}</main>',
    '@media print{.service-report-isolated-actions{display:none!important}.service-visit-print-sheet{display:block!important}}',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: pc-layoutpariteit ontbreekt in mobiele serviceverslag-afdruk ({needle})')

start = built.find('  function serviceReportIsolatedPrintDocument(report) {')
end = built.find('  function printServiceReportIsolated(report) {', start)
block = built[start:end]
for forbidden in ['body{padding:10mm', '@media(max-width:700px){body{padding:6mm', 'serviceReportPrintStylesheet()']:
    if forbidden in block:
        raise SystemExit(f'Buildvalidatie mislukt: oude afwijkende mobiele printlayout is nog aanwezig ({forbidden})')

print('[Machinepark] serviceverslag gsm gebruikt exact dezelfde CSS/printlayout als pc')
