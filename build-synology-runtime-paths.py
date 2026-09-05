from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
MANIFEST = ROOT / "manifest.webmanifest"
AUTH = ROOT / "synology-local-auth.js"

index = INDEX.read_text(encoding="utf-8")

if not AUTH.is_file():
    raise SystemExit("Buildvalidatie mislukt: synology-local-auth.js ontbreekt")
auth_hash = hashlib.sha256(AUTH.read_bytes()).hexdigest()[:12]

# De app draait onder /machinepark/. Absolute /...-paden wijzen dan naar de
# domeinroot en breken features zoals Beheer. Maak alleen runtime-assets relatief.
asset_pattern = re.compile(
    r'(?P<attr>src|href)="/(?P<path>(?:'
    r'machinepark-logo\.svg|'
    r'fault-library\.(?:js|css)(?:\?v=[^"]*)?|'
    r'manual-library\.(?:js|css)(?:\?v=[^"]*)?|'
    r'service-visits\.(?:js|css)(?:\?v=[^"]*)?|'
    r'offline-first\.js(?:\?v=[^"]*)?|'
    r'assets/machinepark-build\.(?:js|css)(?:\?v=[^"]*)?'
    r'))"'
)

index, count = asset_pattern.subn(
    lambda m: f'{m.group("attr")}="./{m.group("path")}"',
    index,
)

if count < 8:
    raise SystemExit(f"Buildvalidatie mislukt: te weinig Synology runtimepaden aangepast ({count})")

remaining = re.findall(
    r'(?:src|href)="/(?:machinepark-logo\.svg|fault-library\.|manual-library\.|service-visits\.|offline-first\.js|assets/machinepark-build\.)[^"]*"',
    index,
)
if remaining:
    raise SystemExit("Buildvalidatie mislukt: absolute Synology runtimepaden blijven over: " + ", ".join(remaining))

INDEX.write_text(index, encoding="utf-8")

sw = SW.read_text(encoding="utf-8")

# Maak de volledige precache-lijst canoniek. Eerdere builders voegen soms
# versiegebonden regels toe; op Synology moeten ze allemaal relatief zijn en
# elke regel moet syntactisch correct door een komma gescheiden worden.
assets_match = re.search(r"const ASSETS=\[(.*?)\];", sw, re.S)
if not assets_match:
    raise SystemExit("Buildvalidatie mislukt: service-worker ASSETS-lijst ontbreekt")

asset_values = re.findall(r"'([^']+)'", assets_match.group(1))
if not asset_values:
    raise SystemExit("Buildvalidatie mislukt: service-worker ASSETS-lijst is leeg")

fixed_assets = []
for value in asset_values:
    if value == "/":
        value = "./"
    elif value.startswith("/") and not value.startswith("/.netlify/"):
        value = "." + value
    fixed_assets.append(value)

auth_asset = f"./synology-local-auth.js?v={auth_hash}"
fixed_assets = [
    value for value in fixed_assets
    if not value.startswith("./synology-local-auth.js")
]
fixed_assets.append(auth_asset)

asset_block = "const ASSETS=[\n" + "\n".join(
    f"  {json.dumps(value)}," for value in fixed_assets
) + "\n];"
sw = sw[:assets_match.start()] + asset_block + sw[assets_match.end():]

sw = sw.replace("c.put('/index.html',copy)", "c.put('./index.html',copy)")
sw = sw.replace("caches.match('/index.html')", "caches.match('./index.html')")

remaining_sw_roots = [
    value for value in fixed_assets
    if value.startswith("/") and not value.startswith("/.netlify/")
]
if remaining_sw_roots:
    raise SystemExit("Buildvalidatie mislukt: service worker bevat nog rootassets: " + ", ".join(remaining_sw_roots))

SW.write_text(sw, encoding="utf-8")

# Loginruntime en service worker zelf krijgen inhoudsversies zodat een oude
# browser/service-worker-cache nooit de vorige logininterface kan blijven tonen.
index = INDEX.read_text(encoding="utf-8")
index, auth_count = re.subn(
    r'src="\./synology-local-auth\.js(?:\?v=[^"]*)?"',
    f'src="./synology-local-auth.js?v={auth_hash}"',
    index,
)
if auth_count != 1:
    raise SystemExit(f"Buildvalidatie mislukt: loginruntime verwacht 1x, gevonden {auth_count}x")

sw_hash = hashlib.sha256(SW.read_bytes()).hexdigest()[:12]
index, sw_count = re.subn(
    r"navigator\.serviceWorker\.register\('\./sw\.js(?:\?v=[^']*)?'(?:,\s*\{[^}]*\})?\)",
    f"navigator.serviceWorker.register('./sw.js?v={sw_hash}', {{updateViaCache:'none'}})",
    index,
)
if sw_count != 1:
    raise SystemExit(f"Buildvalidatie mislukt: service-workerregistratie verwacht 1x, gevonden {sw_count}x")

INDEX.write_text(index, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["start_url"] = "./"
manifest["scope"] = "./"
manifest["description"] = "Lokaal Machinepark voor toestellen, onderhoud, depannages en onderdelen op Synology."
for icon in manifest.get("icons", []):
    src = str(icon.get("src") or "")
    if src.startswith("/"):
        icon["src"] = "." + src
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"[Machinepark] Synology runtimepaden relatief gemaakt ({count} HTML-assets), login v={auth_hash} en service worker v={sw_hash}")
