from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'
js_path = ROOT / 'manual-library.js'
css_path = ROOT / 'manual-library.css'
endpoint_path = ROOT / 'netlify/functions/manual-library.mjs'

index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="manual-library-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


for required in (js_path, css_path, endpoint_path):
    if not required.exists():
        raise SystemExit(f'Buildvalidatie mislukt: {required.name} ontbreekt')

if MARKER not in index:
    nav_anchor = '<button type="button" data-view="parts" onclick="switchView(\'parts\')"><span class="icon">▣</span><span class="label">Onderdelen</span></button>'
    nav_manuals = '<button type="button" data-view="manuals" onclick="switchView(\'manuals\')"><span class="icon">📘</span><span class="label">Handleidingen</span></button>\n      '
    replace_once(nav_anchor, nav_manuals + nav_anchor, 'navigatie Handleidingen')

    view_anchor = '<section class="view" id="view-parts">'
    view_manuals = '''<section class="view" id="view-manuals">
      <div class="toolbar manual-toolbar">
        <div class="toolbar-left">
          <select id="manualBrandFilter" class="filter"><option value="">Alle merken</option></select>
          <select id="manualModelFilter" class="filter"><option value="">Alle modellen</option></select>
          <select id="manualTypeFilter" class="filter"><option value="">Alle types</option></select>
        </div>
        <div class="toolbar-right">
          <button class="btn" type="button" id="refreshManualLibrary">Vernieuwen</button>
          <button class="btn primary" type="button" id="addManualLibraryItem">+ Handleiding toevoegen</button>
        </div>
      </div>
      <div id="manualLibraryStatus" class="muted manual-library-status">Handleidingen laden…</div>
      <div class="table-wrap"><table class="table manual-table"><thead><tr><th>Type</th><th>Handleiding</th><th>Merk / model / toestel</th><th>Versie / taal</th><th>Offline</th><th></th></tr></thead><tbody id="manualLibraryBody"></tbody></table></div>
    </section>

    '''
    replace_once(view_anchor, view_manuals + view_anchor, 'pagina Handleidingen')

    settings_anchor = '        <div class="settings-card"><h4>Toestellen synchroniseren</h4>'
    settings_card = '''        <div class="settings-card" id="manualLibrarySettingsCard">
          <h4>Handleidingen</h4>
          <p>Beheer centrale PDF-handleidingen per merk, model of specifiek toestel. Techniekers kunnen passende handleidingen vanuit Toestellen en Depannages openen en geselecteerde PDF’s offline bewaren.</p>
          <div class="manual-settings-actions">
            <button class="btn" type="button" id="manageManualsFromSettings">Handleidingen bekijken</button>
            <button class="btn primary" type="button" id="addManualFromSettings">+ Handleiding toevoegen</button>
          </div>
        </div>
'''
    replace_once(settings_anchor, settings_card + settings_anchor, 'Beheerkaart Handleidingen')

    if '</head>' not in index or '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken voor handleidingenbibliotheek')
    head_assets = f'''<meta {MARKER}>
<link rel="stylesheet" href="/manual-library.css" data-machinepark-manual-library="css">
'''
    index = index.replace('</head>', head_assets + '</head>', 1)
    loader = '<script src="/manual-library.js" data-machinepark-manual-library="js"></script>\n'
    body_pos = index.rfind('</body>')
    index = index[:body_pos] + loader + index[body_pos:]
    index_path.write_text(index, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
if "'/manual-library.js'" not in sw or "'/manual-library.css'" not in sw:
    anchor = "  '/fault-library.css',\n"
    if sw.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: service-worker assetanker voor handleidingen ontbreekt')
    sw = sw.replace(anchor, anchor + "  '/manual-library.js',\n  '/manual-library.css',\n", 1)
    sw_path.write_text(sw, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
feature = js_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')
required_html = [
    MARKER, 'data-view="manuals"', 'id="view-manuals"', 'id="manualLibrarySettingsCard"',
    '/manual-library.js', '/manual-library.css',
]
required_feature = [
    'MachineparkManualLibraryDB', 'machinepark-manual-files-v1', 'Offline beschikbaar maken',
    'Handleidingen voor dit toestel', 'Handleidingen voor deze depannage', 'manuals.manage',
    'machineparkLoadManualLibrary', 'machineparkOpenManualPdf',
]
required_endpoint = [
    "CONFIG_KEY = 'manual-library-v1'", "FILE_PREFIX = 'manual-files/'", 'application/pdf',
    "action === 'save-manual'", "action === 'delete-manual'", 'MAX_FILE_BYTES',
]
missing = [item for item in required_html if item not in built]
missing += [item for item in required_feature if item not in feature]
missing += [item for item in required_endpoint if item not in endpoint]
if missing:
    raise SystemExit('Buildvalidatie handleidingenbibliotheek mislukt: ' + ', '.join(missing))

print('[Machinepark] centrale PDF-handleidingen per merk/model/toestel met optionele offline opslag actief')
