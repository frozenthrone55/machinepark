from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

# Eenmalige correctie van de bestaande foutieve inventarisreeks.
# Dit is bewust GEEN algemene formatteringsregel: toekomstige toestelcodes blijven vrij invoerbaar.
LEGACY_CODE_FIXES = {f"WCL{number}": f"WCL0{number}" for number in range(501, 560)}
MIGRATION_MARKER = "const LEGACY_DEVICE_CODE_FIXES=Object.freeze("

index = INDEX.read_text(encoding="utf-8")

# Corrigeer ook de ingebouwde inventarisbron voor een volledig nieuwe installatie.
for old_code, new_code in LEGACY_CODE_FIXES.items():
    index = index.replace(
        f'"assetCode":"{old_code}"',
        f'"assetCode":"{new_code}"',
    )

if MIGRATION_MARKER not in index:
    anchor = "async function ensureInventory2025()"
    if anchor not in index:
        raise SystemExit("Legacy toestelcode-correctie: ensureInventory2025 anker ontbreekt")

    mapping = json.dumps(LEGACY_CODE_FIXES, ensure_ascii=False, separators=(",", ":"))
    migration = f'''const LEGACY_DEVICE_CODE_FIXES=Object.freeze({mapping});
async function ensureLegacyDeviceCodeFixes(){{
  const devices=await getAll('devices'),now=new Date().toISOString(),updates=[];
  for(const device of devices){{
    const current=String(device?.assetCode||'').trim().toUpperCase();
    const corrected=LEGACY_DEVICE_CODE_FIXES[current];
    if(!corrected||corrected===current)continue;
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

# Buildvalidatie: huidige bekende foutieve reeks is gecorrigeerd, zonder generieke toekomstige formattering.
for old_code, new_code in LEGACY_CODE_FIXES.items():
    if f'"assetCode":"{old_code}"' in index:
        raise SystemExit(f"Legacy toestelcode-correctie mislukt voor {old_code}")
    if f'"assetCode":"{new_code}"' not in index:
        raise SystemExit(f"Gecorrigeerde toestelcode ontbreekt: {new_code}")

if "assetCode:val(fd,'assetCode')" not in index:
    raise SystemExit("Vrije invoer van toekomstige toestelcodes is onverwacht gewijzigd")

INDEX.write_text(index, encoding="utf-8")
print(f"[Machinepark] {len(LEGACY_CODE_FIXES)} bestaande WCL-codes voorbereid voor eenmalige correctie")
