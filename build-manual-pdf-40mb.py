from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'manual-library.js'
ENDPOINT = ROOT / 'netlify/functions/manual-library.mjs'
SYNOLOGY = ROOT / 'synology/api/manual-library.php'
INDEX = ROOT / 'index.html'
SW = ROOT / 'sw.js'

for path in (CLIENT, ENDPOINT, SYNOLOGY, INDEX, SW):
    if not path.exists():
        raise SystemExit(f'Buildvalidatie mislukt: {path} ontbreekt voor 40 MB handleidingenlimiet')

client = CLIENT.read_text(encoding='utf-8')
client_replacements = {
    "if (file.size > 12_000_000) throw new Error('De PDF is groter dan 12 MB.');":
        "if (file.size > 40_000_000) throw new Error('De PDF is groter dan 40 MB.');",
    'Maximaal 12 MB.': 'Maximaal 40 MB.',
}
for old, new in client_replacements.items():
    if old in client:
        client = client.replace(old, new)
    elif new not in client:
        raise SystemExit(f'Buildvalidatie mislukt: frontend handleidingenlimiet niet gevonden ({old})')
CLIENT.write_text(client, encoding='utf-8')

endpoint = ENDPOINT.read_text(encoding='utf-8')
old_endpoint_limit = 'const MAX_FILE_BYTES = 12_000_000;'
new_endpoint_limit = 'const MAX_FILE_BYTES = 40_000_000;'
if old_endpoint_limit in endpoint:
    endpoint = endpoint.replace(old_endpoint_limit, new_endpoint_limit, 1)
elif new_endpoint_limit not in endpoint:
    raise SystemExit('Buildvalidatie mislukt: Netlify MAX_FILE_BYTES niet gevonden')
endpoint = endpoint.replace('12 MB', '40 MB')
ENDPOINT.write_text(endpoint, encoding='utf-8')

synology = SYNOLOGY.read_text(encoding='utf-8')
old_synology_limit = "define('MP_MANUAL_MAX_BYTES', 12000000);"
new_synology_limit = "define('MP_MANUAL_MAX_BYTES', 40000000);"
if old_synology_limit in synology:
    synology = synology.replace(old_synology_limit, new_synology_limit, 1)
elif new_synology_limit not in synology:
    raise SystemExit('Buildvalidatie mislukt: Synology MP_MANUAL_MAX_BYTES niet gevonden')
synology = synology.replace('12 MB', '40 MB')
SYNOLOGY.write_text(synology, encoding='utf-8')

# 40 MB met blokken van 3,5 MB vereist maximaal 12 uploadblokken.
# Netlify krijgt de limiet uit de chunk-buildlaag; Synology heeft dezelfde
# begrenzing rechtstreeks in de PHP-runtime.
endpoint = ENDPOINT.read_text(encoding='utf-8')
old_chunk_limit = 'const MAX_UPLOAD_CHUNKS = 8;'
new_chunk_limit = 'const MAX_UPLOAD_CHUNKS = 12;'
if old_chunk_limit in endpoint:
    endpoint = endpoint.replace(old_chunk_limit, new_chunk_limit, 1)
elif new_chunk_limit not in endpoint:
    raise SystemExit('Buildvalidatie mislukt: Netlify MAX_UPLOAD_CHUNKS niet gevonden')
ENDPOINT.write_text(endpoint, encoding='utf-8')

synology = SYNOLOGY.read_text(encoding='utf-8')
old_synology_chunks = '$total<1||$total>8)'
new_synology_chunks = '$total<1||$total>12)'
if old_synology_chunks in synology:
    synology = synology.replace(old_synology_chunks, new_synology_chunks, 1)
elif new_synology_chunks not in synology:
    raise SystemExit('Buildvalidatie mislukt: Synology uploadbloklimiet niet gevonden')
SYNOLOGY.write_text(synology, encoding='utf-8')

# Externe handleidingenassets mogen niet op een oude PWA-cache blijven hangen.
# De URL krijgt een inhoudshash, zodat een wijziging ook zonder algemene versiebump
# altijd een nieuw browsercache-key krijgt.
client_bytes = CLIENT.read_bytes()
client_hash = hashlib.sha256(client_bytes).hexdigest()[:12]
index = INDEX.read_text(encoding='utf-8')
script_pattern = re.compile(r'(<script\s+src=["\'](?:\./|/)?manual-library\.js)(?:\?[^"\']*)?(["\'][^>]*data-machinepark-manual-library=["\']js["\'][^>]*></script>)')
index, script_count = script_pattern.subn(rf'\1?v={client_hash}\2', index, count=1)
if script_count != 1:
    raise SystemExit('Buildvalidatie mislukt: loader van manual-library.js niet uniek gevonden voor cache-busting')
INDEX.write_text(index, encoding='utf-8')

# Ook wanneer een toekomstige pagina per ongeluk zonder hash wordt geladen,
# haalt de service worker handleidingenassets online eerst opnieuw op en bewaart
# alleen die nieuwste response als offline fallback.
sw = SW.read_text(encoding='utf-8')
SW_MARKER = '// machinepark-manual-assets-network-first-v1'
if SW_MARKER not in sw:
    anchor = "  if(url.pathname==='/deploy-meta.json'||url.pathname.endsWith('/deploy-meta.json')){\n    e.respondWith(fetch(e.request,{cache:'no-store'}));\n    return;\n  }\n"
    if sw.count(anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: service-worker anker na deploy-meta niet uniek gevonden')
    block = anchor + "\n  // machinepark-manual-assets-network-first-v1\n  if(url.pathname.endsWith('/manual-library.js')||url.pathname.endsWith('/manual-library.css')){\n    e.respondWith(\n      fetch(e.request,{cache:'no-store'}).then(r=>{\n        if(r.ok){const copy=r.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));}\n        return r;\n      }).catch(()=>caches.match(e.request).then(r=>r||Response.error()))\n    );\n    return;\n  }\n"
    sw = sw.replace(anchor, block, 1)
    SW.write_text(sw, encoding='utf-8')

built_client = CLIENT.read_text(encoding='utf-8')
built_endpoint = ENDPOINT.read_text(encoding='utf-8')
built_synology = SYNOLOGY.read_text(encoding='utf-8')
built_index = INDEX.read_text(encoding='utf-8')
built_sw = SW.read_text(encoding='utf-8')
required = [
    (built_client, 'file.size > 40_000_000'),
    (built_client, 'Maximaal 40 MB.'),
    (built_endpoint, 'const MAX_FILE_BYTES = 40_000_000;'),
    (built_synology, "define('MP_MANUAL_MAX_BYTES', 40000000);"),
    (built_endpoint, 'const MAX_UPLOAD_CHUNKS = 12;'),
    (built_synology, '$total<1||$total>12)'),
    (built_index, f'manual-library.js?v={client_hash}'),
    (built_sw, SW_MARKER),
    (built_sw, "url.pathname.endsWith('/manual-library.js')"),
]
missing = [needle for haystack, needle in required if needle not in haystack]
if missing:
    raise SystemExit('Buildvalidatie 40 MB handleidingenlimiet/cachefix mislukt: ' + ', '.join(missing))

for label, source in [('frontend', built_client), ('Netlify', built_endpoint), ('Synology', built_synology)]:
    if '12 MB' in source or '20 MB' in source:
        raise SystemExit(f'Buildvalidatie mislukt: oude 12/20 MB melding blijft aanwezig in {label}')

print(f'[Machinepark] PDF-handleidingen tot 40 MB in max. 12 blokken + cache-busting actief ({client_hash})')
