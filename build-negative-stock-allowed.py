from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")


def replace_exact(old: str, new: str, label: str, expected: int = 1):
    global index
    count = index.count(old)
    if count != expected:
        raise SystemExit(f"Negatieve voorraad: verwacht {expected}x {label}, gevonden {count}x")
    index = index.replace(old, new)


# 1) Onderhoud en depannage: voorraadtekort mag nooit de registratie blokkeren.
# De voorraadmutaties zelf blijven gewoon aftrekken en mogen dus onder nul gaan.
replace_exact(
    "const usage=collectUsage(),err=checkUsage(usage,old.usedParts||[]);if(err){alert(err);return}",
    "const usage=collectUsage()",
    "voorraadblokkade bij service wijzigen",
    expected=2,
)
replace_exact(
    "const err=checkMaintenanceBatchUsage(items);if(err){alert(err);return}",
    "",
    "voorraadblokkade bij onderhoud per locatie",
)
replace_exact(
    "const err=checkBreakdownBatchUsage(items);if(err){alert(err);return}",
    "",
    "voorraadblokkade bij depannage per locatie",
)

# 2) Onderdelen manueel beheren: negatieve voorraad rechtstreeks kunnen opslaan.
replace_exact(
    '<input name="stock" type="number" step="1" min="0" value="${p.stock??0}">',
    '<input name="stock" type="number" step="1" value="${p.stock??0}">',
    "minimum nul op voorraadveld",
)

# 3) Excel-stocktelling: negatieve voorraad is een geldige voorraadstand.
negative_import_guard = "if(!old&&stockNum!==null&&stockNum<0){records.push({artNr,key,action:'skip',reason:'Negatieve voorraad bij nieuw onderdeel',stock:null});continue}"
replace_exact(negative_import_guard, "", "negatieve voorraad overslaan bij nieuw onderdeel")
replace_exact(
    "const stock=old&&(stockNum===null||stockNum<0)?Number(old.stock||0):(stockNum===null?0:Math.round(stockNum));",
    "const stock=stockNum===null?(old?Number(old.stock||0):0):Math.round(stockNum);",
    "negatieve voorraad negeren bij bestaande onderdelen",
)

# 4) Filter 'Geen voorraad' moet negatieve voorraad ook tonen.
replace_exact(
    "(f==='zero'&&stock===0)",
    "(f==='zero'&&stock<=0)",
    "filter geen voorraad",
)

# 5) Helptekst in Beheer in lijn brengen met het nieuwe gedrag.
replace_exact(
    "Bij een bestaande artikelregel met een ongeldige of negatieve voorraad blijft de huidige voorraad behouden, maar de prijs wordt wel bijgewerkt.",
    "Negatieve voorraad is toegestaan en wordt bij de stocktelling gewoon als voorraadstand overgenomen. Bij een ongeldige of lege voorraadwaarde blijft voor een bestaand onderdeel de huidige voorraad behouden.",
    "helptekst stocktelling",
)

# Veiligheidscontroles: aftrekken moet onbegrensd blijven en mag niet op nul worden afgekapt.
required = [
    "stock:Number(p.stock||0)-q",
    "stock:Number(p.stock||0)-qty",
    "const stock=stockNum===null?(old?Number(old.stock||0):0):Math.round(stockNum);",
    '<input name="stock" type="number" step="1" value="${p.stock??0}">',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f"Negatieve voorraad: vereiste werking ontbreekt: {needle}")

for forbidden in [
    "const usage=collectUsage(),err=checkUsage(usage,old.usedParts||[]);if(err){alert(err);return}",
    "const err=checkMaintenanceBatchUsage(items);if(err){alert(err);return}",
    "const err=checkBreakdownBatchUsage(items);if(err){alert(err);return}",
    "Negatieve voorraad bij nieuw onderdeel",
    '<input name="stock" type="number" step="1" min="0"',
]:
    if forbidden in index:
        raise SystemExit(f"Negatieve voorraad: blokkade is nog aanwezig: {forbidden}")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] negatieve voorraad toegestaan bij onderhoud, depannage, manuele stock en Excel-stocktelling")
