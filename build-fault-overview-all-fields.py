from pathlib import Path

ROOT = Path(__file__).resolve().parent
frontend_path = ROOT / 'fault-library.js'
index_path = ROOT / 'index.html'
css_path = ROOT / 'fault-library.css'

frontend = frontend_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

MARKER = '// machinepark-fault-overview-all-fields-v1'
SYNC_MARKER = '// machinepark-fault-overview-live-sync-v1'


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    return text.replace(old, new, 1)


if MARKER not in frontend:
    old_header = '<table class="table fault-table"><thead><tr><th>Code</th><th>Storing</th><th>Categorie</th><th>Merk / model</th><th>Oplossing</th><th></th></tr></thead><tbody id="faultLibraryBody"></tbody></table>'
    new_header = '<table class="table fault-table"><thead><tr><th>Code</th><th>Storing</th><th>Categorie</th><th>Merk</th><th>Model</th><th>Gedetailleerde omschrijving</th><th>Melding</th><th>Symptomen</th><th>Mogelijke oorzaken</th><th>Oplossing 1</th><th>Oplossing 2</th><th>Extra controle / oplossingen</th><th>Interne opmerkingen</th><th>Actief</th><th></th></tr></thead><tbody id="faultLibraryBody"></tbody></table>'
    index = replace_once(index, old_header, new_header, 'volledige storingenoverzicht-kop')

    old_solution = "      const solution = fault.solution1 || fault.solution2 || fault.solutions?.[0] || fault.message || fault.description || '—';"
    new_solution = "      // machinepark-fault-overview-all-fields-v1\n      const overviewText = (value) => String(value ?? '').trim() || '—';\n      const overviewList = (items) => faultLines(items).join(' · ') || '—';\n      // Elke overzichtswaarde wordt bij elke render rechtstreeks uit hetzelfde actuele fault-object gelezen als de detailweergave.\n      const overview = {\n        code: overviewText(fault.code),\n        name: overviewText(fault.name),\n        category: overviewText(fault.category),\n        brand: overviewText(fault.brand),\n        model: overviewText(fault.model),\n        description: overviewText(fault.description),\n        message: overviewText(fault.message),\n        symptoms: overviewList(fault.symptoms),\n        causes: overviewList(fault.causes),\n        solution1: overviewText(fault.solution1),\n        solution2: overviewText(fault.solution2),\n        solutions: overviewList(fault.solutions),\n        notes: overviewText(fault.notes),\n        active: fault.active !== false,\n      };"
    frontend = replace_once(frontend, old_solution, new_solution, 'oude enkelvoudige oplossingskolom')

    old_row = "      return `<tr><td><span class=\"fault-code\">${esc(fault.code || '—')}</span></td><td><span class=\"fault-name\">${esc(fault.name)}</span>${fault.active === false ? ' <span class=\"badge gray\">Inactief</span>' : ''}</td><td>${esc(fault.category || '—')}</td><td>${esc(faultScopeText(fault))}<div class=\"fault-scope\">${faultScopeBadge(fault)}</div></td><td><div class=\"fault-solution-preview\" title=\"${esc(solution)}\">${esc(solution)}</div></td><td><button type=\"button\" class=\"btn small\" data-fault-details=\"${esc(fault.id)}\">Bekijken</button></td></tr>`;"
    new_row = "      return `<tr><td><span class=\"fault-code\">${esc(overview.code)}</span></td><td><span class=\"fault-name\">${esc(overview.name)}</span></td><td>${esc(overview.category)}</td><td>${esc(overview.brand)}</td><td>${esc(overview.model)}</td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.description)}\">${esc(overview.description)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.message)}\">${esc(overview.message)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.symptoms)}\">${esc(overview.symptoms)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.causes)}\">${esc(overview.causes)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.solution1)}\">${esc(overview.solution1)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.solution2)}\">${esc(overview.solution2)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.solutions)}\">${esc(overview.solutions)}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overview.notes)}\">${esc(overview.notes)}</div></td><td>${overview.active ? '<span class=\"badge success\">Ja</span>' : '<span class=\"badge gray\">Nee</span>'}</td><td><button type=\"button\" class=\"btn small\" data-fault-details=\"${esc(fault.id)}\">Bekijken</button></td></tr>`;"
    frontend = replace_once(frontend, old_row, new_row, 'volledige storingenoverzicht-rij')

    colspan_count = frontend.count('colspan="6"')
    if colspan_count != 4:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 4x storingen-colspan 6, gevonden {colspan_count}x')
    frontend = frontend.replace('colspan="6"', 'colspan="15"')

# Het overzicht mag nooit op een oudere lokale snapshot blijven staan wanneer er netwerk is.
# Bij openen van de Storingen-pagina halen we meteen dezelfde centrale faultLibrary opnieuw op;
# de globale live-sync blijft diezelfde lijst daarna elke 3 seconden verversen.
if SYNC_MARKER not in frontend:
    frontend = replace_once(
        frontend,
        '  window.machineparkRenderFaultLibrary = renderFaultLibrary;\n',
        "  window.machineparkRenderFaultLibrary = renderFaultLibrary;\n\n  // machinepark-fault-overview-live-sync-v1\n  let faultOverviewSyncing = null;\n  async function syncFaultOverviewFromCentral() {\n    if (!canViewFaultLibrary() || navigator.onLine === false) return faultLibrary;\n    if (faultOverviewSyncing) return faultOverviewSyncing;\n    faultOverviewSyncing = loadFaultLibrary(true)\n      .then((faults) => {\n        if (state.view === 'faults') renderFaultLibrary();\n        return faults;\n      })\n      .finally(() => { faultOverviewSyncing = null; });\n    return faultOverviewSyncing;\n  }\n  window.machineparkSyncFaultOverview = syncFaultOverviewFromCentral;\n",
        'centrale storingenoverzicht-sync helper',
    )
    frontend = replace_once(
        frontend,
        "    if (state.view === 'faults') renderFaultLibrary();",
        "    if (state.view === 'faults') {\n      renderFaultLibrary();\n      syncFaultOverviewFromCentral().catch(() => {});\n    }",
        'directe centrale refresh bij openen Storingen',
    )
    frontend = replace_once(
        frontend,
        "    if (refresh) refresh.onclick = async () => { faultLibraryLoaded = false; await loadFaultLibrary(true); renderFaultLibrary(); };",
        "    if (refresh) refresh.onclick = async () => { await syncFaultOverviewFromCentral(); };",
        'handmatige storingenrefresh via dezelfde centrale sync',
    )

if '.fault-table{min-width:980px}' in css:
    css = css.replace('.fault-table{min-width:980px}', '.fault-table{min-width:2600px}', 1)
if '.fault-overview-cell{' not in css:
    css += '\n.fault-overview-cell{min-width:145px;max-width:300px;white-space:normal;overflow-wrap:anywhere;line-height:1.4;color:#53615b}\n.fault-table td{vertical-align:top}\n'

frontend_path.write_text(frontend, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')

built_frontend = frontend_path.read_text(encoding='utf-8')
built_index = index_path.read_text(encoding='utf-8')
built_css = css_path.read_text(encoding='utf-8')

required_headers = [
    '<th>Code</th>', '<th>Storing</th>', '<th>Categorie</th>', '<th>Merk</th>', '<th>Model</th>',
    '<th>Gedetailleerde omschrijving</th>', '<th>Melding</th>', '<th>Symptomen</th>',
    '<th>Mogelijke oorzaken</th>', '<th>Oplossing 1</th>', '<th>Oplossing 2</th>',
    '<th>Extra controle / oplossingen</th>', '<th>Interne opmerkingen</th>', '<th>Actief</th>',
]
for needle in required_headers:
    if needle not in built_index:
        raise SystemExit(f'Buildvalidatie mislukt: overzichtskolom ontbreekt ({needle})')
for needle in [
    MARKER,
    'code: overviewText(fault.code)', 'name: overviewText(fault.name)', 'category: overviewText(fault.category)',
    'brand: overviewText(fault.brand)', 'model: overviewText(fault.model)',
    'description: overviewText(fault.description)', 'message: overviewText(fault.message)',
    'symptoms: overviewList(fault.symptoms)', 'causes: overviewList(fault.causes)',
    'solution1: overviewText(fault.solution1)', 'solution2: overviewText(fault.solution2)',
    'solutions: overviewList(fault.solutions)', 'notes: overviewText(fault.notes)',
    'active: fault.active !== false', 'colspan="15"',
    SYNC_MARKER, 'window.machineparkSyncFaultOverview = syncFaultOverviewFromCentral',
    'faultOverviewSyncing = loadFaultLibrary(true)', "syncFaultOverviewFromCentral().catch(() => {})",
]:
    if needle not in built_frontend:
        raise SystemExit(f'Buildvalidatie mislukt: actuele storingswaarde/sync ontbreekt in overzicht ({needle})')
if '.fault-table{min-width:2600px}' not in built_css or '.fault-overview-cell{' not in built_css:
    raise SystemExit('Buildvalidatie mislukt: brede storingenoverzicht-opmaak ontbreekt')

print('[Machinepark] storingenoverzicht toont alle actuele centrale detailwaarden en blijft live gesynchroniseerd')
