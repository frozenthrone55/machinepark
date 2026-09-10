from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

START = "  function serviceIsolatedPrintDocument(kind, record) {"
END = "  function printServiceRecordIsolated(kind, record) {"
OLD = "    const label = kind === 'maintenance' ? 'Onderhoud' : 'Depannage';"
NEW = "    const label = kind === 'maintenance' ? 'Onderhoud' : (record?.serviceKind === 'other' ? (record.workTypeName || 'Andere werken') : 'Depannage');"

start = index.find(START)
end = index.find(END, start + 1) if start >= 0 else -1
if start < 0 or end < 0:
    raise SystemExit("Buildvalidatie mislukt: geïsoleerde werkzaamheidsafdruk niet gevonden")

block = index[start:end]
count = block.count(OLD)
if count != 1:
    raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x geïsoleerde documenttitel, gevonden {count}x")

block = block.replace(OLD, NEW, 1)
index = index[:start] + block + index[end:]

# build-other-works.py verwerkt daarna nog precies de desktop/fallback-versie.
remaining = index.count(OLD)
if remaining != 1:
    raise SystemExit(f"Buildvalidatie mislukt: verwacht nog 1x fallback-documenttitel, gevonden {remaining}x")

index_path.write_text(index, encoding="utf-8")
print("[Machinepark] geïsoleerde gsm-afdruk voorbereid voor Andere werken; fallback blijft apart patchbaar")
