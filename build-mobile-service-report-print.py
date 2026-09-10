from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
js_path = ROOT / 'service-visits.js'
js = js_path.read_text(encoding='utf-8')
MARKER = 'machinepark-mobile-service-report-print-v1'

if MARKER not in js:
    pattern = re.compile(
        r"  async function printServiceReport\(id\)\{.*?\n  \}\n\n  function showServiceReportDetails",
        re.S,
    )
    replacement = r'''  function serviceReportShouldUseIsolatedPrint() {
    const ua=String(navigator.userAgent||'');
    const narrow=typeof window.matchMedia==='function'&&window.matchMedia('(max-width: 900px)').matches;
    const coarse=typeof window.matchMedia==='function'&&window.matchMedia('(pointer: coarse)').matches;
    return narrow||coarse||/Android|iPhone|iPad|iPod|Mobile/i.test(ua);
  }

  function serviceReportPrintStylesheet() {
    return document.querySelector('link[data-machinepark-service-visits="v1"]')?.href || '/service-visits.css';
  }

  function serviceReportIsolatedPrintDocument(report) {
    const title=`Machinepark - Serviceverslag - ${reportDisplayLabel(report)}`;
    const css=serviceReportPrintStylesheet();
    return `<!doctype html><html lang="nl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${svEsc(title)}</title><link rel="stylesheet" href="${svEsc(css)}"><style>
      html,body{margin:0;background:#fff;color:#111}
      body{padding:10mm;box-sizing:border-box}
      .service-visit-print-sheet{display:block!important}
      .service-report-isolated-actions{display:flex;justify-content:flex-end;margin:0 0 7mm}
      .service-report-isolated-actions button{font:inherit;padding:10px 16px;border:1px solid #777;border-radius:8px;background:#fff;color:#111}
      @media(max-width:700px){body{padding:6mm}}
      @media print{body{padding:0}.service-report-isolated-actions{display:none!important}}
    </style></head><body class="service-visit-printing"><div class="service-report-isolated-actions"><button type="button" id="serviceReportPrintNow">Afdrukken / PDF</button></div><main class="service-visit-print-sheet">${reportHtml(report)}</main></body></html>`;
  }

  function printServiceReportIsolated(report) {
    // machinepark-mobile-service-report-print-v1
    // Op gsm wordt alleen het gekozen serviceverslag in een apart document gezet.
    // De hoofdapp en het Werkzaamheden-overzicht bestaan niet in dit printdocument.
    const printWindow=window.open('','_blank');
    if(!printWindow)return false;
    try{
      let printed=false;
      const triggerPrint=()=>{
        if(printed||printWindow.closed)return;
        printed=true;
        try{printWindow.focus();printWindow.print();}catch(_){}
      };
      printWindow.document.open();
      printWindow.document.write(serviceReportIsolatedPrintDocument(report));
      printWindow.document.close();
      const manual=printWindow.document.getElementById('serviceReportPrintNow');
      if(manual)manual.addEventListener('click',()=>{try{printWindow.focus();printWindow.print();}catch(_){}});
      const schedule=()=>setTimeout(triggerPrint,100);
      if(printWindow.document.readyState==='complete')schedule();
      else printWindow.addEventListener('load',schedule,{once:true});
      setTimeout(triggerPrint,4000);
      return true;
    }catch(error){
      console.error('Serviceverslag mobiel afdrukken',error);
      try{printWindow.close();}catch(_){}
      return false;
    }
  }

  async function printServiceReport(id){
    const report=serviceReportById(id)||serviceReportForVisit(id);if(!report){toast('Serviceverslag niet gevonden.');return;}
    window.machineparkSuppressOverviewPrintUntil=Date.now()+15000;
    if(serviceReportShouldUseIsolatedPrint()){
      if(!printServiceReportIsolated(report))alert('Sta pop-ups toe om het serviceverslag af te drukken.');
      return;
    }
    const sheet=ensurePrintSheet();sheet.innerHTML=reportHtml(report);
    const images=[...sheet.querySelectorAll('img')];
    await Promise.all(images.map(img=>img.complete?Promise.resolve():new Promise(resolve=>{const done=()=>resolve();img.addEventListener('load',done,{once:true});img.addEventListener('error',done,{once:true});setTimeout(done,3500);}))); 
    const title=document.title;document.title=`Machinepark - Serviceverslag - ${reportDisplayLabel(report)}`;document.body.classList.add('service-visit-printing');
    const restore=()=>{document.body.classList.remove('service-visit-printing');document.title=title;window.removeEventListener('afterprint',restore);};
    window.addEventListener('afterprint',restore);window.print();setTimeout(()=>{if(document.body.classList.contains('service-visit-printing'))restore();},1800);
  }

  function showServiceReportDetails'''
    js, count = pattern.subn(replacement, js, count=1)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: printServiceReport kon niet eenduidig worden vervangen ({count}x)')

    old = "print.onclick=()=>void printServiceReport(report.id);foot.insertBefore(print,submit);"
    new = "print.onclick=event=>{event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();void printServiceReport(report.id);};foot.insertBefore(print,submit);"
    if js.count(old) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: serviceverslag-afdrukknop verwacht 1x, gevonden {js.count(old)}x')
    js = js.replace(old, new, 1)
    js_path.write_text(js, encoding='utf-8')

built = js_path.read_text(encoding='utf-8')
required = [
    MARKER,
    'serviceReportShouldUseIsolatedPrint',
    'serviceReportIsolatedPrintDocument',
    'printServiceReportIsolated',
    "window.open('','_blank')",
    'serviceReportPrintNow',
    'window.machineparkSuppressOverviewPrintUntil=Date.now()+15000',
    'event.stopImmediatePropagation()',
    '<main class="service-visit-print-sheet">${reportHtml(report)}</main>',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: mobiele serviceverslag-afdruk ontbreekt ({needle})')

block = built[built.index('function printServiceReportIsolated'):built.index('async function printServiceReport', built.index('function printServiceReportIsolated'))]
if 'class="app"' in block or 'view-work' in block:
    raise SystemExit('Buildvalidatie mislukt: geïsoleerd serviceverslag bevat nog app/werkzaamhedenoverzicht')

print('[Machinepark] serviceverslag op gsm afdrukbaar in volledig geïsoleerd printdocument')
