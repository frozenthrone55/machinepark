from pathlib import Path

ROOT = Path(__file__).resolve().parent
frontend_path = ROOT / 'fault-library.js'
index_path = ROOT / 'index.html'
css_path = ROOT / 'fault-library.css'

frontend = frontend_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')

MARKER = '// machinepark-fault-overview-all-fields-v1'


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
    new_solution = "      // machinepark-fault-overview-all-fields-v1\n      const overviewText = (value) => String(value || '').trim() || '—';\n      const overviewList = (items) => Array.isArray(items) && items.length ? items.map((item) => String(item || '').trim()).filter(Boolean).join(' · ') || '—' : '—';"
    frontend = replace_once(frontend, old_solution, new_solution, 'oude enkelvoudige oplossingskolom')

    old_row = "      return `<tr><td><span class=\"fault-code\">${esc(fault.code || '—')}</span></td><td><span class=\"fault-name\">${esc(fault.name)}</span>${fault.active === false ? ' <span class=\"badge gray\">Inactief</span>' : ''}</td><td>${esc(fault.category || '—')}</td><td>${esc(faultScopeText(fault))}<div class=\"fault-scope\">${faultScopeBadge(fault)}</div></td><td><div class=\"fault-solution-preview\" title=\"${esc(solution)}\">${esc(solution)}</div></td><td><button type=\"button\" class=\"btn small\" data-fault-details=\"${esc(fault.id)}\">Bekijken</button></td></tr>`;"
    new_row = "      return `<tr><td><span class=\"fault-code\">${esc(fault.code || '—')}</span></td><td><span class=\"fault-name\">${esc(fault.name || '—')}</span></td><td>${esc(fault.category || '—')}</td><td>${esc(fault.brand || '—')}</td><td>${esc(fault.model || '—')}</td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewText(fault.description))}\">${esc(overviewText(fault.description))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewText(fault.message))}\">${esc(overviewText(fault.message))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewList(fault.symptoms))}\">${esc(overviewList(fault.symptoms))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewList(fault.causes))}\">${esc(overviewList(fault.causes))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewText(fault.solution1))}\">${esc(overviewText(fault.solution1))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewText(fault.solution2))}\">${esc(overviewText(fault.solution2))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewList(fault.solutions))}\">${esc(overviewList(fault.solutions))}</div></td><td><div class=\"fault-overview-cell\" title=\"${esc(overviewText(fault.notes))}\">${esc(overviewText(fault.notes))}</div></td><td>${fault.active === false ? '<span class=\"badge gray\">Nee</span>' : '<span class=\"badge success\">Ja</span>'}</td><td><button type=\"button\" class=\"btn small\" data-fault-details=\"${esc(fault.id)}\">Bekijken</button></td></tr>`;"
    frontend = replace_once(frontend, old_row, new_row, 'volledige storingenoverzicht-rij')

    colspan_count = frontend.count('colspan="6"')
    if colspan_count != 3:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 3x storingen-colspan 6, gevonden {colspan_count}x')
    frontend = frontend.replace('colspan="6"', 'colspan="15"')

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
for needle in [MARKER, 'fault.description', 'fault.message', 'fault.symptoms', 'fault.causes', 'fault.solution1', 'fault.solution2', 'fault.solutions', 'fault.notes', 'colspan="15"']:
    if needle not in built_frontend:
        raise SystemExit(f'Buildvalidatie mislukt: storingswaarde ontbreekt in overzicht ({needle})')
if '.fault-table{min-width:2600px}' not in built_css or '.fault-overview-cell{' not in built_css:
    raise SystemExit('Buildvalidatie mislukt: brede storingenoverzicht-opmaak ontbreekt')

print('[Machinepark] alle invulbare storingsvelden als afzonderlijke overzichtskolommen zichtbaar')
