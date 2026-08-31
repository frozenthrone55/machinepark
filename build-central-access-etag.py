from pathlib import Path

ROOT = Path(__file__).resolve().parent
offline_path = ROOT / 'offline-first.js'
source = offline_path.read_text(encoding='utf-8')
MARKER = '// machinepark-central-access-etag-v1'

old = """      const headers = await centralHeaders(false);
      const etag = meta.etag || centralSync.etag || null;
      if (etag) headers['If-None-Match'] = etag;
      const res = await fetch(CENTRAL_SYNC_URL, { method: 'GET', headers, cache: 'no-store' });"""

new = """      const headers = await centralHeaders(false);
      const etag = meta.etag || centralSync.etag || null;
      // machinepark-central-access-etag-v1
      // Gebruik geen standaard If-None-Match: browsers/CDN's kunnen dan zelf een 304
      // zonder JSON-body produceren, waardoor nieuwe rollen/rechten niet worden toegepast.
      // De server gebruikt deze eigen header alleen voor de Blob-ETag-vergelijking en
      // retourneert altijd JSON met de actuele toegangsrechten.
      if (etag) headers['X-Machinepark-If-None-Match'] = etag;
      const res = await fetch(CENTRAL_SYNC_URL, { method: 'GET', headers, cache: 'no-store' });"""

if MARKER not in source:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 centrale ETag-header, gevonden {count}')
    source = source.replace(old, new, 1)
    offline_path.write_text(source, encoding='utf-8')

built = offline_path.read_text(encoding='utf-8')
for needle in [MARKER, "headers['X-Machinepark-If-None-Match'] = etag", 'applyMachineparkServerAccess(body)']:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: toegangsvriendelijke ETag ontbreekt ({needle})')

anchor = built.find(MARKER)
section = built[anchor:anchor + 900]
if "headers['If-None-Match'] = etag" in section:
    raise SystemExit('Buildvalidatie mislukt: standaard If-None-Match blijft actief in centralPull')

print('[Machinepark] centrale ETag-check behoudt altijd JSON met actuele toegangsrechten')
