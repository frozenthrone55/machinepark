from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-source-reports-v1"'
MARKER = 'data-machinepark-build-fix="composed-device-selection-save-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: verslagtabel ontbreekt voor toestel-opslagfix')

if MARKER not in index:
    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor toestel-opslagfix, gevonden {index.count(anchor)}x')

    script = r'''
  function composedSyncVisibleDeviceSelection(){
    document.querySelectorAll('#composedDeviceBody [data-composed-device]').forEach(cb=>{
      const id=String(cb.dataset.composedDevice||'');if(!id)return;
      if(cb.checked)selectedComposedDevices.add(id);else selectedComposedDevices.delete(id);
    });
    updateComposedSelectedCount();
  }

  const composedReportAwareSaveDocument=saveComposedDocument;
  saveComposedDocument=async function(){
    composedSyncVisibleDeviceSelection();
    return composedReportAwareSaveDocument();
  };

  const composedEnsureUiWithSourceReports=ensureComposedUi;
  ensureComposedUi=function(){
    composedEnsureUiWithSourceReports();
    const saveButton=document.getElementById('composedSaveDocument');
    if(saveButton)saveButton.onclick=()=>saveComposedDocument();
  };
'''
    index = index.replace(anchor, script + '\n' + anchor, 1)
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor toestel-opslagfix')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'function composedSyncVisibleDeviceSelection()',
    "document.querySelectorAll('#composedDeviceBody [data-composed-device]')",
    'if(cb.checked)selectedComposedDevices.add(id)',
    'const composedReportAwareSaveDocument=saveComposedDocument',
    'composedSyncVisibleDeviceSelection();',
    "const saveButton=document.getElementById('composedSaveDocument')",
    'saveButton.onclick=()=>saveComposedDocument()',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: toestel-opslagtoken ontbreekt: {needle}')

print('[Machinepark] samengesteld document kan opnieuw worden opgeslagen met alleen toestellen uit de linkertabel')
