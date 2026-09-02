from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
js_path = ROOT / 'fault-library.js'
css_path = ROOT / 'fault-library.css'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="fault-library-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


if not js_path.exists() or not css_path.exists():
    raise SystemExit('Buildvalidatie mislukt: fault-library.js of fault-library.css ontbreekt')

if MARKER not in index:
    nav_anchor = '<button type="button" data-view="parts" onclick="switchView(\'parts\')"><span class="icon">▣</span><span class="label">Onderdelen</span></button>'
    nav_faults = '<button type="button" data-view="faults" onclick="switchView(\'faults\')"><span class="icon">⚠</span><span class="label">Storingen</span></button>\n      '
    replace_once(nav_anchor, nav_faults + nav_anchor, 'navigatie Storingen')

    view_anchor = '<section class="view" id="view-parts">'
    view_faults = '''<section class="view" id="view-faults">
      <div class="toolbar fault-toolbar">
        <div class="toolbar-left">
          <select id="faultBrandFilter" class="filter"><option value="">Alle merken</option></select>
          <select id="faultModelFilter" class="filter"><option value="">Alle modellen</option></select>
          <select id="faultCategoryFilter" class="filter"><option value="">Alle categorieën</option></select>
        </div>
        <div class="toolbar-right">
          <button class="btn" type="button" id="refreshFaultLibrary">Vernieuwen</button>
          <button class="btn primary" type="button" id="addFaultLibraryItem">+ Storing toevoegen</button>
        </div>
      </div>
      <div id="faultLibraryStatus" class="muted fault-library-status">Storingsbibliotheek laden…</div>
      <div class="table-wrap"><table class="table fault-table"><thead><tr><th>Code</th><th>Storing</th><th>Categorie</th><th>Merk / model</th><th>Oplossing</th><th></th></tr></thead><tbody id="faultLibraryBody"></tbody></table></div>
    </section>

    '''
    replace_once(view_anchor, view_faults + view_anchor, 'pagina Storingen')

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor storingsbibliotheek')
    head_assets = f'''<meta {MARKER}>
<link rel="stylesheet" href="/fault-library.css" data-machinepark-fault-library="css">
'''
    index = index.replace('</head>', head_assets + '</head>', 1)
    loader = '<script src="/fault-library.js" data-machinepark-fault-library="js"></script>\n'
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + loader + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
# Ook een reeds versiegebonden URL telt als bestaande asset. Zo blijft een tweede
# build idempotent en ontstaan er geen dubbele cache-items.
if "'/fault-library.js" not in sw or "'/fault-library.css" not in sw:
    anchor = "  '/offline-first.js',\n"
    if sw.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: service-worker assetanker voor storingsbibliotheek ontbreekt')
    sw = sw.replace(anchor, anchor + "  '/fault-library.js',\n  '/fault-library.css',\n", 1)
    sw_path.write_text(sw, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
feature = js_path.read_text(encoding='utf-8')
required_html = [
    MARKER, 'data-view="faults"', 'id="view-faults"', '/fault-library.js', '/fault-library.css',
]
required_feature = [
    'Storingscode / nummer', 'Leeg = alle merken', 'Leeg = alle modellen van het merk',
    'Mogelijke oorzaken', 'Controle / oplossingen', 'faultRef', 'view.faults', 'faults.manage',
    'MachineparkFaultLibraryDB', 'Storingsbibliotheek', 'data-fault-pick',
]
missing = [item for item in required_html if item not in built]
missing += [item for item in required_feature if item not in feature]
if missing:
    raise SystemExit('Buildvalidatie storingsbibliotheek mislukt: ' + ', '.join(missing))

print('[Machinepark] storingsbibliotheek met optionele code, merk/modelkoppeling en offline cache actief')