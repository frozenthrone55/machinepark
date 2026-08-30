from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / 'index.html'
ASSET_DIR = ROOT / 'assets'
JS_PATH = ASSET_DIR / 'machinepark-build.js'
CSS_PATH = ASSET_DIR / 'machinepark-build.css'
PACKAGE = json.loads((ROOT / 'package.json').read_text(encoding='utf-8'))
VERSION = str(PACKAGE.get('version') or '1')

index = INDEX_PATH.read_text(encoding='utf-8')
marker_re = re.compile(r'data-machinepark-build-fix="([^"]+)"')
style_re = re.compile(r'<style\b([^>]*)data-machinepark-build-fix="([^"]+)"([^>]*)>([\s\S]*?)</style>', re.IGNORECASE)
script_re = re.compile(r'<script\b([^>]*)data-machinepark-build-fix="([^"]+)"([^>]*)>([\s\S]*?)</script>', re.IGNORECASE)

styles = []
scripts = []
markers = []


def take_style(match):
    marker = match.group(2)
    markers.append(marker)
    styles.append(f'/* {marker} */\n{match.group(4).strip()}\n')
    return ''


def take_script(match):
    marker = match.group(2)
    markers.append(marker)
    scripts.append(f'/* {marker} */\n{match.group(4).strip()}\n')
    return ''

index = style_re.sub(take_style, index)
index = script_re.sub(take_script, index)

if not styles and not scripts:
    if JS_PATH.exists() and CSS_PATH.exists():
        print('[Machinepark] externe build-assets reeds aanwezig')
        raise SystemExit(0)
    raise SystemExit('Buildvalidatie mislukt: geen feature-assets gevonden om uit te splitsen')

ASSET_DIR.mkdir(parents=True, exist_ok=True)
CSS_PATH.write_text('\n'.join(styles).strip() + '\n', encoding='utf-8')
JS_PATH.write_text("'use strict';\n\n" + '\n'.join(scripts).strip() + '\n', encoding='utf-8')

# Bewaar alle buildmarkers in de HTML zodat een tweede build de patches niet opnieuw toepast.
unique_markers = []
seen = set()
for marker in markers:
    if marker not in seen:
        seen.add(marker)
        unique_markers.append(marker)
marker_html = '\n'.join(f'<meta data-machinepark-build-fix="{marker}">' for marker in unique_markers)

css_tag = f'<link rel="stylesheet" href="/assets/machinepark-build.css?v={VERSION}" data-machinepark-generated-asset="css">'
js_tag = f'<script src="/assets/machinepark-build.js?v={VERSION}" data-machinepark-generated-asset="js"></script>'

# Verwijder eventuele tags van een eerdere finalize-run en plaats één canonieke set.
index = re.sub(r'\s*<link[^>]+data-machinepark-generated-asset="css"[^>]*>', '', index)
index = re.sub(r'\s*<script[^>]+data-machinepark-generated-asset="js"[^>]*></script>', '', index)

if '</head>' not in index or '</body>' not in index:
    raise SystemExit('Buildvalidatie mislukt: HTML-afsluiters ontbreken bij asset-extractie')

index = index.replace('</head>', f'\n{marker_html}\n{css_tag}\n</head>', 1)
body_pos = index.rfind('</body>')
index = index[:body_pos] + f'\n{js_tag}\n' + index[body_pos:]
INDEX_PATH.write_text(index, encoding='utf-8')

if marker_re.search(JS_PATH.read_text(encoding='utf-8')):
    raise SystemExit('Buildvalidatie mislukt: buildmarkers zijn onverwacht in gegenereerde JS terechtgekomen')

print(f'[Machinepark] frontend opgesplitst: {JS_PATH.stat().st_size / 1024:.1f} KB JS, {CSS_PATH.stat().st_size / 1024:.1f} KB CSS')
