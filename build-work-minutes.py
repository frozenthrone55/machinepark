from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")

MARKER = 'data-machinepark-build-fix="work-minutes-v1"'


def replace_exact(old, new, expected=None, label='waarde'):
    global index
    count = index.count(old)
    if expected is not None and count != expected:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht {expected}x {label}, gevonden {count}x")
    if count == 0:
        raise SystemExit(f"Buildvalidatie mislukt: {label} niet gevonden")
    index = index.replace(old, new)


if MARKER not in index:
    # Alle zichtbare werkduurvelden worden in minuten ingevoerd.
    replace_exact(
        'name="hours" type="number" min="0" step="0.25"',
        'name="hours" type="number" min="0" step="1"',
        4,
        'werkduurvelden',
    )
    index = index.replace('Werkuren depannage *', 'Werkminuten depannage *')
    index = index.replace('Werkuren onderhoud *', 'Werkminuten onderhoud *')
    index = index.replace("${b.batchId?'Werkuren depannage':'Werkuren'}", "${b.batchId?'Werkminuten depannage':'Werkminuten'}")
    index = index.replace("${m.batchId?'Werkuren onderhoud':'Werkuren'}", "${m.batchId?'Werkminuten onderhoud':'Werkminuten'}")
    index = index.replace('placeholder="bv. 2"', 'placeholder="bv. 120"')

    # Bestaande opgeslagen waarden blijven decimale uren voor achterwaartse compatibiliteit.
    # Bij openen wordt uren -> minuten omgerekend, bij opslaan minuten -> uren.
    replace_exact(
        'value="${b.hours??\'\'}"',
        'value="${Number(b.hours||0)>0?Math.round(Number(b.hours)*60):\'\'}"',
        1,
        'depannage werkduurwaarde',
    )
    replace_exact(
        'value="${m.hours??\'\'}"',
        'value="${Number(m.hours||0)>0?Math.round(Number(m.hours)*60):\'\'}"',
        1,
        'onderhoud werkduurwaarde',
    )
    replace_exact(
        "hours:Number(fd.get('hours')||0)",
        "hours:Number(fd.get('hours')||0)/60",
        2,
        'werkduur opslaan bij bewerken',
    )
    replace_exact(
        "hours=Number(fd.get('hours')||0)",
        "hours=Number(fd.get('hours')||0)/60",
        2,
        'werkduur opslaan bij locatiebeurt',
    )

    # Overzichten, details en afdrukken tonen minuten.
    replace_exact(
        "const hourText=hours.toLocaleString('nl-BE',{maximumFractionDigits:2});return `${hourText} u /",
        "const minutes=Math.round(hours*60);return `${minutes} min /",
        2,
        'werkduursamenvattingen',
    )
    index = index.replace('Werkuren / toestellen', 'Werkminuten / toestellen')
    index = index.replace('Deze uren gelden voor de volledige depannagegroep', 'Deze minuten gelden voor de volledige depannagegroep')
    index = index.replace('Deze uren gelden voor de volledige onderhoudsgroep', 'Deze minuten gelden voor de volledige onderhoudsgroep')
    index = index.replace('Werkuren, datum, uur en technieker gelden', 'Werkminuten, datum, uur en technieker gelden')
    index = index.replace('De werkuren gelden voor de volledige locatiebeurt', 'De werkminuten gelden voor de volledige locatiebeurt')

    index = index.replace('</body>', f'<span {MARKER} hidden></span></body>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'Werkminuten depannage *',
    'Werkminuten onderhoud *',
    'Werkminuten / toestellen',
    'Math.round(Number(b.hours)*60)',
    'Math.round(Number(m.hours)*60)',
    "hours:Number(fd.get('hours')||0)/60",
    "hours=Number(fd.get('hours')||0)/60",
    '`${minutes} min / ${count}',
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: minutenregistratie ontbreekt ({needle})')

if ' u / ${count}' in index:
    raise SystemExit('Buildvalidatie mislukt: werkduur wordt nog in uren weergegeven')

print('[Machinepark] alle werkduurregistraties worden in minuten getoond en ingevoerd')
