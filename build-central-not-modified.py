from pathlib import Path

ROOT = Path(__file__).resolve().parent
offline_path = ROOT / 'offline-first.js'
source = offline_path.read_text(encoding='utf-8')
MARKER = '// machinepark-central-304-not-modified-v1'

old = """      const res = await fetch(CENTRAL_SYNC_URL, { method: 'GET', headers, cache: 'no-store' });
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(body.error || text || `Cloud ophalen mislukt (${res.status})`);
      if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);

      if (!body.exists) {"""

new = """      const res = await fetch(CENTRAL_SYNC_URL, { method: 'GET', headers, cache: 'no-store' });
      // machinepark-central-304-not-modified-v1
      // 304 betekent dat de ETag nog actueel is. Dit is een geslaagde synchronisatie,
      // geen foutrespons. Laat de bestaande lokale snapshot onaangeroerd.
      if (res.status === 304) {
        centralSync.etag = etag || centralSync.etag || null;
        await writeMeta({ etag: centralSync.etag || null, dirty: false });
        if (!quiet) setCentralSyncStatus('☁ Centraal gesynchroniseerd · geen wijzigingen', 'ok');
        return { exists: true, unchanged: true, data: null, etag: centralSync.etag };
      }
      const text = await res.text();
      let body = {};
      try { body = text ? JSON.parse(text) : {}; } catch (_) {}
      if (!res.ok) throw new Error(body.error || text || `Cloud ophalen mislukt (${res.status})`);
      if (typeof window.applyMachineparkServerAccess === 'function') window.applyMachineparkServerAccess(body);

      if (!body.exists) {"""

if MARKER not in source:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 ETag centrale GET, gevonden {count}')
    source = source.replace(old, new, 1)
    offline_path.write_text(source, encoding='utf-8')

built = offline_path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'if (res.status === 304)',
    "unchanged: true",
    'Centraal gesynchroniseerd · geen wijzigingen',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: 304-afhandeling ontbreekt ({needle})')

# Controleer dat de 304-check vóór de algemene !res.ok-fout staat in centralPull.
anchor = built.find("const etag = meta.etag || centralSync.etag || null;")
end = built.find("if (!body.exists)", anchor)
section = built[anchor:end]
if section.find('if (res.status === 304)') < 0 or section.find('if (!res.ok)') < 0:
    raise SystemExit('Buildvalidatie mislukt: centrale 304- of foutafhandeling niet gevonden')
if section.find('if (res.status === 304)') > section.find('if (!res.ok)'):
    raise SystemExit('Buildvalidatie mislukt: 304 wordt pas na de algemene foutcontrole behandeld')

print('[Machinepark] HTTP 304 wordt als geldige, ongewijzigde centrale synchronisatie behandeld')
