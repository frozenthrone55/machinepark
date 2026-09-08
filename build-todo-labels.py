from pathlib import Path
from hashlib import sha256
import re

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SERVICE = ROOT / "service-visits.js"

index = INDEX.read_text(encoding="utf-8")
service = SERVICE.read_text(encoding="utf-8")

# Alleen zichtbare terminologie van de Acties-module wijzigen.
# Technische identifiers zoals state.actions, actionId en datastore-namen blijven
# bewust ongewijzigd om compatibiliteit en bestaande data te behouden.
replacements = [
    ("Snelle acties en opvolging.", "Snelle ToDo’s en opvolging."),
    ("Nieuwe actie snel toevoegen…", "Nieuwe ToDo snel toevoegen…"),
    ("+ Nieuwe actie met details", "+ Nieuwe ToDo met details"),
    ("Alle uitgevoerde acties", "Alle uitgevoerde ToDo’s"),
    ("Geen openstaande acties.", "Geen openstaande ToDo’s."),
    ("Nog geen uitgevoerde acties in deze periode.", "Nog geen uitgevoerde ToDo’s in deze periode."),
    ("Er zijn geen open of in behandeling zijnde acties om te koppelen.", "Er zijn geen open of in behandeling zijnde ToDo’s om te koppelen."),
    ("Er zijn geen openstaande acties om te koppelen.", "Er zijn geen openstaande ToDo’s om te koppelen."),
    ("Kies één of meer acties voor dit serviceverslag.", "Kies één of meer ToDo’s voor dit serviceverslag."),
    ("Gekoppelde acties (", "Gekoppelde ToDo’s ("),
    ("Acties koppelen", "ToDo’s koppelen"),
    ("Acties (", "ToDo’s ("),
    ("Open acties", "Open ToDo’s"),
    ("Alle acties", "Alle ToDo’s"),
    ("Mijn acties", "Mijn ToDo’s"),
    ("Zoek in acties…", "Zoek in ToDo’s…"),
    ("Bestaande actie koppelen aan serviceverslag", "Bestaande ToDo koppelen aan serviceverslag"),
    ("Bestaande actie koppelen", "Bestaande ToDo koppelen"),
    ("Kies een actie met status", "Kies een ToDo met status"),
    ("Nog geen actie gekoppeld.", "Nog geen ToDo gekoppeld."),
    ("Deze uitgevoerde actie opnieuw bij Nog te doen plaatsen?", "Deze uitgevoerde ToDo opnieuw bij Nog te doen plaatsen?"),
    ("Vul een actie in.", "Vul een ToDo in."),
    ("+ Actie maken", "+ ToDo maken"),
    ("Actie koppelen aan serviceverslag", "ToDo koppelen aan serviceverslag"),
    ("Actie koppelen mislukt.", "ToDo koppelen mislukt."),
    ("Actie koppelen", "ToDo koppelen"),
    ("Actie gekoppeld aan serviceconcept", "ToDo gekoppeld aan serviceconcept"),
    ("Actie gekoppeld aan serviceverslag", "ToDo gekoppeld aan serviceverslag"),
    ("Actie losgekoppeld", "ToDo losgekoppeld"),
    ("Actie niet gevonden.", "ToDo niet gevonden."),
    ("Actie afronden", "ToDo afronden"),
    ("Actie afgerond", "ToDo afgerond"),
    ("Actie bewerken", "ToDo bewerken"),
    ("Actie opslaan", "ToDo opslaan"),
    ("Actie bijgewerkt", "ToDo bijgewerkt"),
    ("Actie toegevoegd", "ToDo toegevoegd"),
    ("Actie uitgevoerd", "ToDo uitgevoerd"),
    ("Actie verwijderd", "ToDo verwijderd"),
    ("Actie verwijderen mislukt.", "ToDo verwijderen mislukt."),
    ("Actie verwijderen", "ToDo verwijderen"),
    ("Actie opnieuw geopend", "ToDo opnieuw geopend"),
    ("Actie heropend", "ToDo heropend"),
    ("Actie snel aangemaakt", "ToDo snel aangemaakt"),
    ("Actie aangemaakt", "ToDo aangemaakt"),
    ("Actie gewijzigd", "ToDo gewijzigd"),
    ("Actie staat op ", "ToDo staat op "),
    ("Actie “", "ToDo “"),
    ("Actiekoppeling is nog niet geladen.", "ToDo-koppeling is nog niet geladen."),
    ("Actiekoppeling verwijderd", "ToDo-koppeling verwijderd"),
    ("Actiekoppeling serviceconcept finaliseren", "ToDo-koppeling serviceconcept finaliseren"),
    ("Actiekoppeling verwijderd serviceconcept opruimen", "ToDo-koppeling verwijderd serviceconcept opruimen"),
    ("actiekoppeling kon niet bijgewerkt worden.", "ToDo-koppeling kon niet bijgewerkt worden."),
    ('<div class="event-label action">Actie</div>', '<div class="event-label action">ToDo</div>'),
    ('<span class="event-label action">Actie</span>', '<span class="event-label action">ToDo</span>'),
    ('<label>Actie *</label>', '<label>ToDo *</label>'),
    ('<label>Actie</label><select name="actionId">', '<label>ToDo</label><select name="actionId">'),
    ("showModal('Actie',", "showModal('ToDo',"),
    ("item.title||'Actie'", "item.title||'ToDo'"),
    ("a.title||'Actie'", "a.title||'ToDo'"),
    ("title||'Actie'", "title||'ToDo'"),
]

for old, new in replacements:
    index = index.replace(old, new)
    service = service.replace(old, new)

# De module zelf heet exact 'ToDo' in navigatie en paginatitel.
index = index.replace('<span class="label">Acties</span>', '<span class="label">ToDo</span>')
index = index.replace("actions: ['Acties',", "actions: ['ToDo',")
index = index.replace('actions: ["Acties",', 'actions: ["ToDo",')
index = index.replace("actions:['Acties',", "actions:['ToDo',")
index = index.replace('actions:["Acties",', 'actions:["ToDo",')

required = [
    '<span class="label">ToDo</span>',
    "Nieuwe ToDo snel toevoegen…",
    "+ Nieuwe ToDo met details",
    "Alle ToDo’s",
    "Mijn ToDo’s",
    "Open ToDo’s",
    "ToDo afronden",
    "Bestaande ToDo koppelen",
    "Gekoppelde ToDo’s",
    "event-label action\">ToDo",
]
combined = index + "\n" + service
for needle in required:
    if needle not in combined:
        raise SystemExit("Buildvalidatie mislukt: ToDo-label ontbreekt (" + needle + ")")

for forbidden in [
    '<span class="label">Acties</span>',
    "Nieuwe actie snel toevoegen…",
    "+ Nieuwe actie met details",
    "Alle acties",
    "Mijn acties",
    "Open acties",
    "Gekoppelde acties",
    "Acties koppelen",
    "Bestaande actie koppelen",
    "Actie koppelen",
    "Actie afronden",
]:
    if forbidden in combined:
        raise SystemExit("Buildvalidatie mislukt: oude Acties-naam nog zichtbaar (" + forbidden + ")")

service_version = sha256(service.encode("utf-8")).hexdigest()[:12]
pattern = r'(service-visits\.js\?v=)[^"\'\s>]+'
index, count = re.subn(pattern, lambda match: match.group(1) + service_version, index, count=1)
if count != 1:
    raise SystemExit("Buildvalidatie mislukt: service-visits cacheversie niet gevonden")

SERVICE.write_text(service, encoding="utf-8")
INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] zichtbare Acties-module volledig hernoemd naar ToDo")
