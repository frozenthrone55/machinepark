from pathlib import Path
import re

root = Path('.')
index_path = root / 'index.html'
text = index_path.read_text(encoding='utf-8')

# Dashboard: restore original KPI dot.
old_kpi = '<div class="kpi"><img class="kpi-device-icon" src="/machinepark-coffee-device-icon.png" alt="" aria-hidden="true"><div class="label">Actieve toestellen</div>'
new_kpi = '<div class="kpi"><span class="dot"></span><div class="label">Actieve toestellen</div>'
if old_kpi not in text:
    raise SystemExit('Dashboard koffietoestelicoon niet gevonden')
text = text.replace(old_kpi, new_kpi, 1)

# Sidebar: replace coffee emoji with the approved transparent machine icon.
old_nav = '<button type="button" data-view="devices" onclick="switchView(\'devices\')"><span class="icon">☕</span><span class="label">Toestellen</span></button>'
new_nav = '<button type="button" data-view="devices" onclick="switchView(\'devices\')"><span class="icon"><img class="device-nav-icon" src="/machinepark-coffee-device-icon.png" alt="" aria-hidden="true"></span><span class="label">Toestellen</span></button>'
if old_nav not in text:
    raise SystemExit('Navigatieknop Toestellen niet gevonden')
text = text.replace(old_nav, new_nav, 1)

# Replace dashboard-only icon styling with navigation styling.
old_css = '.kpi-device-icon{float:right;width:34px;height:34px;object-fit:contain;margin:-2px -2px 0 10px;opacity:.96}'
new_css = '.device-nav-icon{display:block;width:21px;height:21px;object-fit:contain;filter:brightness(0) invert(1);opacity:.82}.nav button:hover .device-nav-icon,.nav button.active .device-nav-icon{opacity:1}'
if old_css not in text:
    raise SystemExit('Oude KPI-icoonstijl niet gevonden')
text = text.replace(old_css, new_css, 1)

text = text.replace('v1.61 • Koffietoestelicoon dashboard', 'v1.62 • Koffietoestelicoon in navigatie')
index_path.write_text(text, encoding='utf-8')

# Service worker: force refresh on desktop/mobile and keep the icon offline.
sw_path = root / 'sw.js'
sw = sw_path.read_text(encoding='utf-8')
sw = re.sub(r"const CACHE='[^']+';", "const CACHE='machinepark-v1.62-nav-coffee-icon';", sw, count=1)
if '/machinepark-coffee-device-icon.png' not in sw:
    sw = sw.replace("'/machinepark-logo.svg'", "'/machinepark-logo.svg','/machinepark-coffee-device-icon.png'")
sw_path.write_text(sw, encoding='utf-8')

# Build validator.
validator_path = root / 'scripts' / 'build-machinepark.py'
v = validator_path.read_text(encoding='utf-8')
v = v.replace('"onderdelen navigatie": "data-view=\\"parts\\"",', '"onderdelen navigatie": "data-view=\\"parts\\"",\n    "wit koffietoestel navigatie-icoon": "class=\\"device-nav-icon\\"",\n    "dashboard toestelbolletje": "<span class=\\"dot\\"></span><div class=\\"label\\">Actieve toestellen</div>",')
v = re.sub(r'machinepark-v[0-9.]+-[^\"]+', 'machinepark-v1.62-nav-coffee-icon', v)
validator_path.write_text(v, encoding='utf-8')

# Smoke test.
test_path = root / 'tests' / 'build-smoke.test.mjs'
t = test_path.read_text(encoding='utf-8')
if "class=\"device-nav-icon\"" not in t:
    t = t.replace("    'data-view=\"parts\"',\n", "    'data-view=\"parts\"',\n    'class=\"device-nav-icon\"',\n    '<span class=\"dot\"></span><div class=\"label\">Actieve toestellen</div>',\n")
t = re.sub(r'machinepark-v[0-9.]+-[^\']+', 'machinepark-v1.62-nav-coffee-icon', t)
test_path.write_text(t, encoding='utf-8')

# Package version.
pkg_path = root / 'package.json'
pkg = pkg_path.read_text(encoding='utf-8').replace('"version": "1.60.0"', '"version": "1.62.0"')
pkg_path.write_text(pkg, encoding='utf-8')
