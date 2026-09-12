from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
HISTORY_MARKER = 'data-machinepark-build-fix="composed-history-photos-v1"'
TODO_MARKER = 'data-machinepark-build-fix="composed-todos-v1"'
MARKER = 'data-machinepark-build-fix="composed-pdf-print-parity-v1"'

index = INDEX.read_text(encoding='utf-8')
if HISTORY_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: afdrukweergave ontbreekt voor PDF/print-pariteit')
if TODO_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: ToDo-opname ontbreekt voor PDF/print-pariteit')

if MARKER not in index:
    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor PDF/print-pariteit, gevonden {index.count(anchor)}x')

    script = r'''
  // PDF opslaan gebruikt bewust exact dezelfde browser-afdrukweergave.
  // Daardoor blijven HTML, printStyles(), kaders, fotos en paginering identiek.
  saveComposedPdf=async function(doc,button){
    const old=button?.textContent;
    if(button){button.disabled=true;button.textContent='PDF openen…';}
    try{
      composedNotify('PDF gebruikt dezelfde afdrukweergave. Kies “Opslaan als PDF” in het afdrukvenster.');
      printComposedDocument(doc);
    }finally{
      if(button){button.disabled=false;button.textContent=old;}
    }
  };
'''
    index = index.replace(anchor, script + '\n' + anchor, 1)
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor PDF/print-pariteit')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'saveComposedPdf=async function(doc,button)',
    "button.textContent='PDF openen…'",
    'printComposedDocument(doc);',
    'PDF gebruikt dezelfde afdrukweergave.',
    'Opslaan als PDF',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: PDF/print-pariteit-token ontbreekt: {needle}')

print('[Machinepark] PDF opslaan gebruikt exact dezelfde afdrukweergave als Afdrukken')
