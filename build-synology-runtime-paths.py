from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
MANIFEST = ROOT / "manifest.webmanifest"

index = INDEX.read_text(encoding="utf-8")

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
for old, new in [
    ("  '/',", "  './',"),
    ("  '/index.html',", "  './index.html',"),
    ("  '/manifest.webmanifest',", "  './manifest.webmanifest',"),
    ("  '/machinepark-logo.svg',", "  './machinepark-logo.svg',"),
    ("  '/machinepark-coffee-device-icon.png',", "  './machinepark-coffee-device-icon.png',"),
    ("  '/offline-first.js',", "  './offline-first.js',"),
]:
    sw = sw.replace(old, new)

sw = re.sub(
    r"'/assets/machinepark-build\.js(\?v=[^']*)'",
    r"'./assets/machinepark-build.js\1'",
    sw,
)
sw = re.sub(
    r"'/assets/machinepark-build\.css(\?v=[^']*)'",
    r"'./assets/machinepark-build.css\1'",
    sw,
)
sw = re.sub(
    r"'/fault-library\.js(\?v=[^']*)?'",
    lambda m: "'./fault-library.js" + (m.group(1) or "") + "'",
    sw,
)
sw = re.sub(
    r"'/fault-library\.css(\?v=[^']*)?'",
    lambda m: "'./fault-library.css" + (m.group(1) or "") + "'",
    sw,
)
sw = sw.replace("c.put('/index.html',copy)", "c.put('./index.html',copy)")
sw = sw.replace("caches.match('/index.html')", "caches.match('./index.html')")

for forbidden in [
    "  '/index.html',",
    "  '/offline-first.js',",
    "'/assets/machinepark-build.js",
    "'/assets/machinepark-build.css",
]:
    if forbidden in sw:
        raise SystemExit(f"Buildvalidatie mislukt: service worker bevat nog rootpad {forbidden}")

SW.write_text(sw, encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["start_url"] = "./"
manifest["scope"] = "./"
manifest["description"] = "Lokaal Machinepark voor toestellen, onderhoud, depannages en onderdelen op Synology."
for icon in manifest.get("icons", []):
    src = str(icon.get("src") or "")
    if src.startswith("/"):
        icon["src"] = "." + src
MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print(f"[Machinepark] Synology runtimepaden relatief gemaakt ({count} HTML-assets) en service worker op /machinepark/ afgestemd")
