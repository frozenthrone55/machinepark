from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'manual-library.js'
ENDPOINT = ROOT / 'netlify/functions/manual-library.mjs'
SYNOLOGY = ROOT / 'synology/api/manual-library.php'

for path in (CLIENT, ENDPOINT, SYNOLOGY):
    if not path.exists():
        raise SystemExit(f'Buildvalidatie mislukt: {path} ontbreekt voor 20 MB handleidingenlimiet')

client = CLIENT.read_text(encoding='utf-8')
client_replacements = {
    "if (file.size > 12_000_000) throw new Error('De PDF is groter dan 12 MB.');":
        "if (file.size > 20_000_000) throw new Error('De PDF is groter dan 20 MB.');",
    'Maximaal 12 MB.': 'Maximaal 20 MB.',
}
for old, new in client_replacements.items():
    if old in client:
        client = client.replace(old, new)
    elif new not in client:
        raise SystemExit(f'Buildvalidatie mislukt: frontend handleidingenlimiet niet gevonden ({old})')
CLIENT.write_text(client, encoding='utf-8')

endpoint = ENDPOINT.read_text(encoding='utf-8')
old_endpoint_limit = 'const MAX_FILE_BYTES = 12_000_000;'
new_endpoint_limit = 'const MAX_FILE_BYTES = 20_000_000;'
if old_endpoint_limit in endpoint:
    endpoint = endpoint.replace(old_endpoint_limit, new_endpoint_limit, 1)
elif new_endpoint_limit not in endpoint:
    raise SystemExit('Buildvalidatie mislukt: Netlify MAX_FILE_BYTES niet gevonden')
endpoint = endpoint.replace('12 MB', '20 MB')
ENDPOINT.write_text(endpoint, encoding='utf-8')

synology = SYNOLOGY.read_text(encoding='utf-8')
old_synology_limit = "define('MP_MANUAL_MAX_BYTES', 12000000);"
new_synology_limit = "define('MP_MANUAL_MAX_BYTES', 20000000);"
if old_synology_limit in synology:
    synology = synology.replace(old_synology_limit, new_synology_limit, 1)
elif new_synology_limit not in synology:
    raise SystemExit('Buildvalidatie mislukt: Synology MP_MANUAL_MAX_BYTES niet gevonden')
synology = synology.replace('12 MB', '20 MB')
SYNOLOGY.write_text(synology, encoding='utf-8')

built_client = CLIENT.read_text(encoding='utf-8')
built_endpoint = ENDPOINT.read_text(encoding='utf-8')
built_synology = SYNOLOGY.read_text(encoding='utf-8')
required = [
    (built_client, 'file.size > 20_000_000'),
    (built_client, 'Maximaal 20 MB.'),
    (built_endpoint, 'const MAX_FILE_BYTES = 20_000_000;'),
    (built_synology, "define('MP_MANUAL_MAX_BYTES', 20000000);"),
]
missing = [needle for haystack, needle in required if needle not in haystack]
if missing:
    raise SystemExit('Buildvalidatie 20 MB handleidingenlimiet mislukt: ' + ', '.join(missing))

for label, source in [('frontend', built_client), ('Netlify', built_endpoint), ('Synology', built_synology)]:
    if '12 MB' in source:
        raise SystemExit(f'Buildvalidatie mislukt: oude 12 MB melding blijft aanwezig in {label}')

print('[Machinepark] PDF-handleidingen tot maximaal 20 MB toegestaan in frontend, Netlify en Synology')
