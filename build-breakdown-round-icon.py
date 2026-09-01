from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')

MARKER = 'machinepark-breakdown-round-icon-v1'
old_icon = '<button type="button" data-view="breakdowns" onclick="switchView(\'breakdowns\')"><span class="icon">⚠</span><span class="label">Depannages</span></button>'
new_icon = '<button type="button" data-view="breakdowns" onclick="switchView(\'breakdowns\')"><span class="icon"><svg class="breakdown-nav-icon-svg" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 7.5v6"></path><path d="M12 16.5h.01"></path></svg></span><span class="label">Depannages</span></button>'

if MARKER not in index:
    if index.count(old_icon) != 1:
        raise SystemExit('Buildvalidatie mislukt: depannage-menu-icoon niet uniek gevonden')
    index = index.replace(old_icon, new_icon, 1)

    style_anchor = '.device-nav-icon-svg{display:block;width:20px;height:20px;stroke:#fff;fill:none;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;opacity:1}'
    if index.count(style_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: navigatie-icoonstijl niet uniek gevonden')
    round_style = '.breakdown-nav-icon-svg{display:block;width:20px;height:20px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;opacity:1}/* ' + MARKER + ' */'
    index = index.replace(style_anchor, style_anchor + round_style, 1)
    index_path.write_text(index, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    'class="breakdown-nav-icon-svg"',
    '<circle cx="12" cy="12" r="8.5"></circle>',
    '<path d="M12 7.5v6"></path>',
    '<path d="M12 16.5h.01"></path>',
]
missing = [needle for needle in required if needle not in built]
if missing:
    raise SystemExit('Buildvalidatie rond depannage-icoon mislukt: ' + ', '.join(missing))

nav_fragment = built.split('data-view="breakdowns"', 1)[1].split('</button>', 1)[0]
if '⚠' in nav_fragment:
    raise SystemExit('Buildvalidatie mislukt: driehoekicoon staat nog in Depannages-menu')

print('[Machinepark] depannage-menu gebruikt rond uitroepteken-icoon')
