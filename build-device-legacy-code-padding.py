from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

# Eenmalige correctie van de bestaande toestelcodes met exact drie cijfers.
# Dit is bewust GEEN algemene formatteringsregel: toekomstige toestelcodes blijven vrij invoerbaar.
# Alleen toestellen die al bestonden op het moment van deze correctie vallen onder de migratie.
LEGACY_CUTOFF = "2026-09-03T17:15:00.000Z"
MIGRATION_MARKER = "const LEGACY_DEVICE_CODE_PATTERN=/^([A-Z]+)(\\d{3})$/;"

index = INDEX.read_text(encoding="utf-8")

# Corrigeer alle driecijferige codes in de ingebouwde bestaande inventarisbron.
# Voorbeelden: WCL123 -> WCL0123, WCL510 -> WCL0510, WCL559 -> WCL0559.
seed_pattern = re.compile(r'(\"assetCode\":\")([A-Za-z]+)(\d{3})(\")')
index, seed_fix_count = seed_pattern.subn(
    lambda m: f'{m.group(1)}{m.group(2)}0{m.group(3)}{m.group(4)}',
    index,
)

if MIGRATION_MARKER not in index:
    anchor = "async function ensureInventory2025()"
    if anchor not in index:
        raise SystemExit("Legacy toestelcode-correctie: ensureInventory2025 anker ontbreekt")

    migration = f'''const LEGACY_DEVICE_CODE_PATTERN=/^([A-Z]+)(\\d{{3}})$/;
const LEGACY_DEVICE_CODE_CUTOFF='{LEGACY_CUTOFF}';
async function ensureLegacyDeviceCodeFixes(){{
  const devices=await getAll('devices'),now=new Date().toISOString(),cutoff=Date.parse(LEGACY_DEVICE_CODE_CUTOFF),updates=[];
  for(const device of devices){{
    const current=String(device?.assetCode||'').trim().toUpperCase();
    const match=current.match(LEGACY_DEVICE_CODE_PATTERN);
    if(!match)continue;
    const createdAt=Date.parse(String(device?.createdAt||''));
    if(Number.isFinite(createdAt)&&createdAt>cutoff)continue;
    const corrected=`${{match[1]}}0${{match[2]}}`;
    if(corrected===current)continue;
    updates.push({{...device,assetCode:corrected,updatedAt:now}});
  }}
  if(updates.length)await putMany('devices',updates);
  return updates.length;
}}
'''
    index = index.replace(anchor, migration + anchor, 1)

startup_anchor = "bind();await refresh();centralSync.enabled=true;startCentralPolling();"
startup_replacement = "const legacyDeviceCodeFixes=await ensureLegacyDeviceCodeFixes();bind();await refresh();centralSync.enabled=true;if(legacyDeviceCodeFixes){try{await centralPush()}catch(syncErr){console.warn('Eenmalige toestelcode-correctie kon nog niet centraal worden opgeslagen:',syncErr)}}startCentralPolling();"
if startup_replacement not in index:
    if startup_anchor not in index:
        raise SystemExit("Legacy toestelcode-correctie: startup anker ontbreekt")
    index = index.replace(startup_anchor, startup_replacement, 1)

# Buildvalidatie: in de bestaande ingebouwde inventaris mag geen code met exact drie cijfers meer staan.
remaining_seed_code = seed_pattern.search(index)
if remaining_seed_code:
    raise SystemExit(f"Driecijferige bestaande toestelcode niet gecorrigeerd: {remaining_seed_code.group(0)}")

for old_code, new_code in (("WCL501", "WCL0501"), ("WCL510", "WCL0510"), ("WCL559", "WCL0559")):
    if f'\"assetCode\":\"{old_code}\"' in index:
        raise SystemExit(f"Legacy toestelcode-correctie mislukt voor {old_code}")
    if f'\"assetCode\":\"{new_code}\"' not in index:
        raise SystemExit(f"Gecorrigeerde toestelcode ontbreekt: {new_code}")

if "assetCode:val(fd,'assetCode')" not in index:
    raise SystemExit("Vrije invoer van toekomstige toestelcodes is onverwacht gewijzigd")

INDEX.write_text(index, encoding="utf-8")
print(f"[Machinepark] {seed_fix_count} bestaande driecijferige toestelcodes voorbereid voor eenmalige correctie")
