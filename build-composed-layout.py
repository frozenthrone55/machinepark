from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-documents-v1"'
SEARCH_MARKER = 'data-machinepark-build-fix="composed-search-filter-v1"'
MARKER = 'data-machinepark-build-fix="composed-layout-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: samengestelde documenten ontbreken voor layout-fix')
if SEARCH_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: zoekfilter moet vóór de layout-fix gebouwd zijn')

if MARKER not in index:
    old_create = '''        <div class="composed-create-grid"><div class="field"><label>Naam / firma van het document</label><input id="composedDocumentName" maxlength="140" placeholder="Bijv. Firma X · volledig toesteldossier"></div><div class="field"><label>Zoek firma, locatie of toestel</label><input id="composedDeviceSearch" type="search" autocomplete="off" placeholder="Typ locatie, WCL-nummer, merk, model of serienummer…"></div></div>
        <div class="composed-toolbar"><div class="composed-toolbar-left"><button class="btn small" id="composedSelectVisible" type="button">Alles zichtbaar aanvinken</button><button class="btn small" id="composedClearSelection" type="button">Selectie wissen</button></div><div class="composed-toolbar-right"><button class="btn primary" id="composedSaveDocument" type="button">Opslaan in samengestelde documenten</button></div></div>
        <div class="table-wrap"><table class="table composed-device-table">'''
    new_create = '''        <div class="composed-create-grid composed-create-grid-single"><div class="field"><label>Naam / firma van het document</label><input id="composedDocumentName" maxlength="140" placeholder="Bijv. Firma X · volledig toesteldossier"></div></div>
        <div class="composed-toolbar"><div class="composed-toolbar-left"><button class="btn small" id="composedSelectVisible" type="button">Alles zichtbaar aanvinken</button><button class="btn small" id="composedClearSelection" type="button">Selectie wissen</button></div><div class="composed-toolbar-right"><button class="btn primary" id="composedSaveDocument" type="button">Opslaan in samengestelde documenten</button></div></div>
        <div class="composed-table-search"><label for="composedDeviceSearch">Zoek firma, locatie of toestel</label><input id="composedDeviceSearch" type="search" autocomplete="off" placeholder="Typ locatie, WCL-nummer, merk, model of serienummer…"></div>
        <div class="table-wrap composed-device-list-wrap"><table class="table composed-device-table">'''

    old_saved = '''      <section class="composed-section"><div class="composed-section-head"><h3>Samengestelde documenten</h3><input class="composed-saved-search" id="composedSavedSearch" type="search" autocomplete="off" placeholder="Zoek in opgeslagen documenten…"></div><div class="composed-section-body"><div class="table-wrap"><table class="table" style="min-width:900px">'''
    new_saved = '''      <section class="composed-section"><div class="composed-section-head"><h3>Samengestelde documenten</h3></div><div class="composed-section-body"><div class="composed-table-search composed-table-search-saved"><label for="composedSavedSearch">Zoek in opgeslagen documenten</label><input class="composed-saved-search" id="composedSavedSearch" type="search" autocomplete="off" placeholder="Typ naam, firma of toestel…"></div><div class="table-wrap"><table class="table" style="min-width:900px">'''

    for old, new, label in [
        (old_create, new_create, 'zoekbalk en scrollzone nieuwe documenten'),
        (old_saved, new_saved, 'zoekbalk opgeslagen documenten'),
    ]:
        count = index.count(old)
        if count != 1:
            raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
        index = index.replace(old, new, 1)

    style = r'''
<style data-machinepark-build-fix="composed-layout-v1">
.composed-create-grid-single{grid-template-columns:minmax(220px,1fr)}
.composed-table-search{display:grid;gap:6px;width:min(520px,100%);margin:4px 0 10px}
.composed-table-search label{font-size:12px;font-weight:750;color:#4f5d57}
.composed-table-search input{width:100%;border:1px solid var(--line);border-radius:10px;padding:9px 11px;background:#fff;outline:none}
.composed-table-search input:focus{border-color:#7ea598;box-shadow:0 0 0 3px rgba(44,106,88,.09)}
.composed-table-search-saved{width:min(420px,100%)}
.composed-device-list-wrap{max-height:min(52vh,520px);overflow:auto;overscroll-behavior:contain}
.composed-device-list-wrap .table th{top:0;z-index:1}
@media(max-width:760px){.composed-device-list-wrap{max-height:55vh}.composed-table-search{width:100%}}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor layout-fix')
    index = index.replace('</head>', style + '</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'composed-create-grid composed-create-grid-single',
    '<label for="composedDeviceSearch">Zoek firma, locatie of toestel</label>',
    'table-wrap composed-device-list-wrap',
    '<label for="composedSavedSearch">Zoek in opgeslagen documenten</label>',
    'max-height:min(52vh,520px)',
    'overscroll-behavior:contain',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: layout-token ontbreekt: {needle}')

print('[Machinepark] samengestelde documentlijst is scrollbaar en zoekvelden staan boven hun tabel')
