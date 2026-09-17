from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
SERVICE = ROOT / 'service-visits.js'
MARKER = 'data-machinepark-build-fix="safe-explicit-print-v1"'
GUARD_MARKER = 'data-machinepark-explicit-print-guard="v1"'

index = INDEX.read_text(encoding='utf-8')
service = SERVICE.read_text(encoding='utf-8')

# 1. Service/depannage/onderhoud: los printdocument openen mag nooit zelf
# printen. Alleen de zichtbare knop in dat document mag printWindow.print().
record_pattern = re.compile(
    r"  function printServiceRecordIsolated\(kind, record\) \{.*?\n  \}\n\n  function printServiceRecord\(kind, id\) \{",
    re.S,
)
record_replacement = '''  function printServiceRecordIsolated(kind, record) {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return false;
    try {
      printWindow.document.open();
      printWindow.document.write(serviceIsolatedPrintDocument(kind, record));
      printWindow.document.close();
      const manualButton = printWindow.document.getElementById('servicePrintNow');
      if (manualButton) manualButton.addEventListener('click', () => {
        try { printWindow.focus(); printWindow.print(); } catch (_) {}
      });
      return true;
    } catch (_) {
      try { printWindow.close(); } catch (_) {}
      return false;
    }
  }

  function printServiceRecord(kind, id) {'''
index, record_count = record_pattern.subn(lambda _match: record_replacement, index, count=1)
if record_count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: veilige service-afdruk kon niet eenduidig worden geplaatst ({record_count}x)')

# 2. Serviceverslagen: idem, met behoud van mobiele fotogroepering.
report_pattern = re.compile(
    r"  function printServiceReportIsolated\(report\) \{.*?\n  \}\n\n  async function printServiceReport\(id\)\{",
    re.S,
)
report_replacement = '''  function printServiceReportIsolated(report) {
    // machinepark-safe-explicit-print-v1
    const printWindow=window.open('','_blank');
    if(!printWindow)return false;
    try{
      printWindow.document.open();
      printWindow.document.write(serviceReportIsolatedPrintDocument(report));
      printWindow.document.close();
      if(typeof serviceReportGroupPhotoRows==='function')serviceReportGroupPhotoRows(printWindow.document);
      const manual=printWindow.document.getElementById('serviceReportPrintNow');
      if(manual)manual.addEventListener('click',()=>{
        try{printWindow.focus();printWindow.print();}catch(_){}
      });
      return true;
    }catch(error){
      console.error('Serviceverslag mobiel afdrukken',error);
      try{printWindow.close();}catch(_){}
      return false;
    }
  }

  async function printServiceReport(id){'''
service, report_count = report_pattern.subn(lambda _match: report_replacement, service, count=1)
if report_count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: veilige serviceverslag-afdruk kon niet eenduidig worden geplaatst ({report_count}x)')

# 3. ToDo: wijzig uitsluitend het automatische foto-wacht/printdeel binnen de
# bestaande functie. Zo blijven alle latere ToDo-aanpassingen onaangeraakt.
action_start_match = re.search(r"function printAction\(id\)\s*\{", index)
action_end_match = re.search(r"\n\s*function openActionDetails\(id\)\s*\{", index[action_start_match.end():] if action_start_match else '')
if not action_start_match or not action_end_match:
    raise SystemExit('Buildvalidatie mislukt: grenzen van ToDo-afdrukfunctie niet gevonden')
action_start = action_start_match.start()
action_end = action_start_match.end() + action_end_match.start()
action_block = index[action_start:action_end]
auto_pattern = re.compile(
    r"\s*const images=\[\.\.\.printWindow\.document\.images\];.*?setTimeout\(\(\)=>\{if\(pending>0\)finish\(\);\},1800\);",
    re.S,
)
manual_action = '''
    const manual=printWindow.document.createElement('button');
    manual.id='machineparkActionPrintNow';
    manual.type='button';
    manual.textContent='Afdrukken / PDF';
    manual.style.cssText='font:inherit;padding:10px 16px;border:1px solid #777;border-radius:8px;background:#fff;color:#111;margin:0 0 14px';
    const hide=printWindow.document.createElement('style');
    hide.textContent='@media print{#machineparkActionPrintNow{display:none!important}}';
    printWindow.document.head.appendChild(hide);
    printWindow.document.body.insertBefore(manual,printWindow.document.body.firstChild);
    manual.addEventListener('click',()=>{try{printWindow.focus();printWindow.print();}catch(_){}});'''
action_block, action_count = auto_pattern.subn(lambda _match: manual_action, action_block, count=1)
if action_count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: automatische ToDo-printtimer niet eenduidig gevonden ({action_count}x)')
index = index[:action_start] + action_block + index[action_end:]

# 4. Samengestelde documenten: geen script-in-script en geen print op load.
# De parent koppelt de zichtbare knop pas na document.close() aan print().
composed_pattern = re.compile(
    r"  function printComposedDocument\(doc\)\{.*?\n\n  function loadJsPdf\(\)",
    re.S,
)
composed_replacement = '''  function printComposedDocument(doc){
    const win=window.open('','_blank');
    if(!win){alert('Het afdrukvenster kon niet worden geopend. Sta pop-ups toe en probeer opnieuw.');return;}
    win.document.open();
    win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${composedEsc(doc.name||'Samengesteld document')}</title><style>${printStyles()}.machinepark-explicit-print-actions{display:flex;justify-content:flex-end;margin:0 0 12px}.machinepark-explicit-print-actions button{font:inherit;padding:10px 16px;border:1px solid #777;border-radius:8px;background:#fff;color:#111}@media print{.machinepark-explicit-print-actions{display:none!important}}</style></head><body><div class="machinepark-explicit-print-actions"><button type="button" id="machineparkComposedPrintNow">Afdrukken / PDF</button></div><main class="composed-document">${documentHtml(doc)}</main></body></html>`);
    win.document.close();
    const manual=win.document.getElementById('machineparkComposedPrintNow');
    if(manual)manual.addEventListener('click',()=>{try{win.focus();win.print();}catch(_){}});
  }

  function loadJsPdf()'''
index, composed_count = composed_pattern.subn(lambda _match: composed_replacement, index, count=1)
if composed_count != 1:
    raise SystemExit(f'Buildvalidatie mislukt: veilige samengestelde afdruk kon niet eenduidig worden geplaatst ({composed_count}x)')

# 5. Hoofdvenster: programmatisch window.print() werkt alleen kort na een echte
# gebruikersklik op een zichtbare print/PDF-bediening. Browser Ctrl+P blijft
# volledig buiten deze JavaScript-guard.
if GUARD_MARKER not in index:
    guard = r'''
<script data-machinepark-explicit-print-guard="v1">
(() => {
  const nativePrint = window.print.bind(window);
  let explicitPrintUntil = 0;
  function grantPrintIntent(ms = 20000) {
    explicitPrintUntil = Date.now() + Math.max(1000, Number(ms) || 20000);
  }
  function hasPrintIntent() {
    return Date.now() <= explicitPrintUntil;
  }
  window.machineparkGrantPrintIntent = grantPrintIntent;
  window.machineparkHasPrintIntent = hasPrintIntent;
  window.print = function() {
    if (!hasPrintIntent()) {
      console.warn('[Machinepark] automatische printopdracht geblokkeerd');
      return false;
    }
    explicitPrintUntil = 0;
    return nativePrint();
  };
  document.addEventListener('click', event => {
    if (!event.isTrusted) return;
    const control = event.target.closest('button,a,[role="button"]');
    if (!control) return;
    const label = `${control.textContent || ''} ${control.getAttribute('aria-label') || ''} ${control.title || ''}`.toLowerCase();
    const known = control.matches('.page-print-btn,.service-detail-print-btn,#printDeviceDetails,.service-visit-print-btn,[data-composed-action="print"],[data-composed-action="pdf"],#composedPreviewPrint,#composedPreviewPdf');
    if (known || /afdruk|print|pdf/.test(label)) grantPrintIntent();
  }, true);
})();
</script>
'''
    body_end = index.rfind('</body>')
    if body_end < 0:
        raise SystemExit('Buildvalidatie mislukt: finale </body> ontbreekt voor printbeveiliging')
    index = index[:body_end] + guard + index[body_end:]

if MARKER not in index:
    head_end = index.find('</head>')
    if head_end < 0:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor printbeveiligingsmarker')
    index = index[:head_end] + f'<meta {MARKER}>\n' + index[head_end:]

INDEX.write_text(index, encoding='utf-8')
SERVICE.write_text(service, encoding='utf-8')

# Eindvalidatie: bekende automatische print-na-load/timerconstructies mogen in
# de finale runtime niet meer voorkomen.
built_index = INDEX.read_text(encoding='utf-8')
built_service = SERVICE.read_text(encoding='utf-8')
forbidden_index = [
    "window.onload=()=>setTimeout(()=>window.print(),120)",
    'setTimeout(triggerPrint, 80)',
    'setTimeout(triggerPrint, 1500)',
    "const finish=()=>setTimeout(()=>{try{printWindow.focus();printWindow.print();}catch(_){}},120)",
]
for needle in forbidden_index:
    if needle in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: automatische printtrigger bleef in index.html ({needle})')

report_start = built_service.find('  function printServiceReportIsolated(report) {')
report_end = built_service.find('  async function printServiceReport(id){', report_start)
if report_start < 0 or report_end < 0:
    raise SystemExit('Buildvalidatie mislukt: veilige serviceverslag-afdruk ontbreekt')
report_block = built_service[report_start:report_end]
for needle in ['triggerPrint', 'setTimeout(triggerPrint']:
    if needle in report_block:
        raise SystemExit(f'Buildvalidatie mislukt: automatische serviceverslag-print bleef actief ({needle})')

required_index = [
    MARKER,
    GUARD_MARKER,
    'event.isTrusted',
    'window.machineparkGrantPrintIntent',
    'automatische printopdracht geblokkeerd',
    'machineparkComposedPrintNow',
    'machineparkActionPrintNow',
    'servicePrintNow',
]
for needle in required_index:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: printbeveiliging ontbreekt ({needle})')

script_at = built_index.rfind(GUARD_MARKER)
final_body_at = built_index.rfind('</body>')
if script_at < 0 or final_body_at < 0 or script_at > final_body_at:
    raise SystemExit('Buildvalidatie mislukt: printbeveiliging staat niet voor de finale body-tag')
if 'serviceReportPrintNow' not in built_service or 'machinepark-safe-explicit-print-v1' not in built_service:
    raise SystemExit('Buildvalidatie mislukt: serviceverslag vereist nog geen expliciete printklik')

print('[Machinepark] automatische printertriggers verwijderd; printen vereist expliciete gebruikersklik')
