from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-documents-v1"'
MARKER = 'data-machinepark-build-fix="composed-search-filter-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: samengestelde documenten ontbreken voor zoekfilter-fix')

if MARKER not in index:
    old_device_handler = "    document.getElementById('composedDeviceSearch').oninput=e=>{composedDeviceQuery=e.target.value||'';renderComposedDevices();};"
    new_device_handler = """    const composedDocumentName=document.getElementById('composedDocumentName');
    const syncComposedDocumentFilter=()=>{composedDeviceQuery=String(composedDocumentName?.value||'');renderComposedDevices();};
    composedDocumentName?.addEventListener('input',syncComposedDocumentFilter);
    composedDocumentName?.addEventListener('search',syncComposedDocumentFilter);"""

    old_saved_handler = "    document.getElementById('composedSavedSearch').oninput=e=>{composedSavedQuery=e.target.value||'';renderComposedSavedTable();};"
    new_saved_handler = """    const composedSavedSearch=document.getElementById('composedSavedSearch');
    const syncComposedSavedSearch=()=>{composedSavedQuery=String(composedSavedSearch?.value||'');renderComposedSavedTable();};
    composedSavedSearch?.addEventListener('input',syncComposedSavedSearch);
    composedSavedSearch?.addEventListener('search',syncComposedSavedSearch);"""

    old_device_filter = """  function composedFilteredDevices(){
    const q=composedKey(composedDeviceQuery);"""
    new_device_filter = """  function composedFilteredDevices(){
    const search=document.getElementById('composedDocumentName');
    composedDeviceQuery=String(search?.value??composedDeviceQuery??'');
    const q=composedKey(composedDeviceQuery);"""

    old_saved_filter = "    const q=composedKey(composedSavedQuery),list=[...composedList()].filter(doc=>!q||"
    new_saved_filter = "    const search=document.getElementById('composedSavedSearch');composedSavedQuery=String(search?.value??composedSavedQuery??'');const q=composedKey(composedSavedQuery),list=[...composedList()].filter(doc=>!q||"

    replacements = [
        (old_device_handler, new_device_handler, 'documentnaam als zoekfilter toestellentabel'),
        (old_saved_handler, new_saved_handler, 'zoeklistener opgeslagen documenten'),
        (old_device_filter, new_device_filter, 'actuele documentnaam als zoekwaarde toestellentabel'),
        (old_saved_filter, new_saved_filter, 'actuele zoekwaarde opgeslagen documenten'),
    ]
    for old, new, label in replacements:
        count = index.count(old)
        if count != 1:
            raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
        index = index.replace(old, new, 1)

    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor zoekfilter-fix')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    "const composedDocumentName=document.getElementById('composedDocumentName')",
    "composedDocumentName?.addEventListener('input',syncComposedDocumentFilter)",
    "composedDocumentName?.addEventListener('search',syncComposedDocumentFilter)",
    "composedSavedSearch?.addEventListener('input',syncComposedSavedSearch)",
    "composedSavedSearch?.addEventListener('search',syncComposedSavedSearch)",
    "const search=document.getElementById('composedDocumentName')",
    "composedDeviceQuery=String(search?.value??composedDeviceQuery??'')",
    "composedSavedQuery=String(search?.value??composedSavedQuery??'')",
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: zoekfilter-token ontbreekt: {needle}')

print('[Machinepark] documentnaam filtert de toestellen live en opgeslagen documenten hebben een eigen zoekveld')
runpy.run_path(str(ROOT / 'build-composed-layout.py'), run_name='__main__')
