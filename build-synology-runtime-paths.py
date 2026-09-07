from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
MANIFEST = ROOT / "manifest.webmanifest"
AUTH = ROOT / "synology-local-auth.js"
OFFLINE = ROOT / "offline-first.js"

index = INDEX.read_text(encoding="utf-8")

if not AUTH.is_file():
    raise SystemExit("Buildvalidatie mislukt: synology-local-auth.js ontbreekt")
auth_hash = hashlib.sha256(AUTH.read_bytes()).hexdigest()[:12]
if not OFFLINE.is_file():
    raise SystemExit("Buildvalidatie mislukt: offline-first.js ontbreekt")
offline_hash = hashlib.sha256(OFFLINE.read_bytes()).hexdigest()[:12]

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

# Op Synology geen volledige app meer tijdens service-worker-installatie
# vooruit downloaden. Op een externe mobiele verbinding veroorzaakte dat een
# tweede, gelijktijdige download van vrijwel alle runtimebestanden. De normale
# fetch-handler bewaart gebruikte bestanden daarna automatisch in de cache.
fixed_assets = [
    value for value in fixed_assets
    if value in {
        "./manifest.webmanifest",
        "./machinepark-logo.svg",
        "./machinepark-coffee-device-icon.png",
    }
]

asset_block = "const ASSETS=[\n" + "\n".join(
    f"  {json.dumps(value)}," for value in fixed_assets
) + "\n];"
sw = sw[:assets_match.start()] + asset_block + sw[assets_match.end():]

sw = sw.replace("c.put('/index.html',copy)", "c.put('./index.html',copy)")
sw = sw.replace("caches.match('/index.html')", "caches.match('./index.html')")

# Synology PHP API mag nooit via de service-worker assetcache lopen.
# Dit is essentieel voor ETag-conflictherstel: na een 409 moet de volgende GET
# gegarandeerd de actuele state-v1.json/ETag van de NAS ophalen.
fetch_anchor = "  if(url.hostname!==self.location.hostname)return;"
fetch_bypass = """  if(url.hostname!==self.location.hostname)return;

  // machinepark-synology-api-network-only-v1
  if(url.pathname.includes('/synology/api/') || e.request.cache==='no-store'){
    e.respondWith(fetch(e.request));
    return;
  }"""
if fetch_anchor not in sw:
    raise SystemExit("Buildvalidatie mislukt: service-worker hostname-anker ontbreekt")
sw = sw.replace(fetch_anchor, fetch_bypass, 1)

remaining_sw_roots = [
    value for value in fixed_assets
    if value.startswith("/") and not value.startswith("/.netlify/")
]
if remaining_sw_roots:
    raise SystemExit("Buildvalidatie mislukt: service worker bevat nog rootassets: " + ", ".join(remaining_sw_roots))

SW.write_text(sw, encoding="utf-8")

# Toon bovenaan het Synology-dashboard wanneer de gepubliceerde runtime gebouwd is.
# De bron is deploy-meta.json uit synology-deploy; daardoor verandert dit automatisch
# bij elke geslaagde publicatie en blijft de tijd los van browser-/serviceworkercache.
DASHBOARD_VERSION_MARKER = 'data-machinepark-synology-version="v2"'
index = INDEX.read_text(encoding="utf-8")
if DASHBOARD_VERSION_MARKER not in index:
    sync_anchor = '<div id="centralSyncStatus" class="sync-status" role="status" aria-live="polite">☁ Verbinden met centrale gegevens…</div>'
    dashboard_stamp = sync_anchor + '<div id="dashboardVersionStamp" class="dashboard-version-stamp" data-machinepark-synology-version="v2" role="status" aria-live="polite">Laatste versie: laden…</div>'
    if sync_anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: synchronisatiestatus ontbreekt voor versiedatum")
    index = index.replace(sync_anchor, dashboard_stamp, 1)

    dashboard_style = """<style data-machinepark-synology-version="v2">
.dashboard-version-stamp{display:flex;align-items:center;width:max-content;max-width:100%;margin-top:7px;padding:7px 10px;border:1px solid #c7d9d2;border-radius:9px;background:#eef6f2;color:#164f3e;font-size:12px;font-weight:800;line-height:1.2;box-shadow:0 1px 0 rgba(16,78,58,.05)}
.dashboard-version-stamp::before{content:'↻';display:inline-block;margin-right:6px;font-size:12px}
@media(max-width:700px){.dashboard-version-stamp{font-size:11px;margin-top:6px}}
</style>
"""
    if "</head>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-head ontbreekt voor versiedatum")
    index = index.replace("</head>", dashboard_style + "</head>", 1)

    dashboard_script = """<script data-machinepark-synology-version="v1">
(() => {
  async function machineparkLoadDashboardVersion() {
    const node = document.getElementById('dashboardVersionStamp');
    if (!node) return;
    try {
      const response = await fetch('./deploy-meta.json?ts=' + Date.now(), {
        cache: 'no-store',
        credentials: 'same-origin'
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const meta = await response.json();
      const date = new Date(meta && meta.built_at ? meta.built_at : '');
      if (!Number.isFinite(date.getTime())) throw new Error('Ongeldige buildtijd');
      const formatted = new Intl.DateTimeFormat('nl-BE', {
        timeZone: 'Europe/Brussels',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      }).format(date).replace(',', '');
      node.textContent = 'Laatste versie: ' + formatted;
    } catch (_) {
      node.textContent = 'Laatste versie: niet beschikbaar';
    }
  }
  window.machineparkRefreshDashboardVersion = machineparkLoadDashboardVersion;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', machineparkLoadDashboardVersion, {once:true});
  } else {
    machineparkLoadDashboardVersion();
  }
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) machineparkLoadDashboardVersion();
  });
})();
</script>
"""
    if "</body>" not in index:
        raise SystemExit("Buildvalidatie mislukt: HTML-body ontbreekt voor versiedatum")
    index = index.replace("</body>", dashboard_script + "</body>", 1)
    INDEX.write_text(index, encoding="utf-8")

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

index, offline_count = re.subn(
    r'src="\./offline-first\.js(?:\?v=[^"]*)?"',
    f'src="./offline-first.js?v={offline_hash}"',
    index,
)
if offline_count != 1:
    raise SystemExit(f"Buildvalidatie mislukt: offline runtime verwacht 1x, gevonden {offline_count}x")

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

print(f"[Machinepark] Synology runtimepaden relatief gemaakt ({count} HTML-assets), login v={auth_hash}, offline v={offline_hash} en service worker v={sw_hash}")
