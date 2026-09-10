from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / 'netlify/functions/_shared/permissions.mjs'
MARKER = '// machinepark-complete-role-permissions-prep-v1'

text = PATH.read_text(encoding='utf-8')
if MARKER not in text:
    # build-manual-native-sync draait eerder en voegt Handleidingen al toe.
    # De complete rollenlaag voegt Handleidingen samen met ToDo en de overige
    # ontbrekende rechten toe. Breng alleen deze tussentijdse catalogmutatie
    # terug naar de basisvorm die de complete laag atomair verwacht.
    view = "  { group: 'Weergave', key: 'view.manuals', label: 'Handleidingen bekijken' },\n"
    manage = "  { group: 'Handleidingen', key: 'manuals.manage', label: 'Handleidingen beheren' },\n"
    if text.count(view) != 1 or text.count(manage) != 1:
        raise SystemExit('Buildvalidatie mislukt: tussentijdse handleidingenrechten niet uniek')
    text = text.replace(view, '', 1).replace(manage, '', 1)

    with_manual = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts'"
    without_manual = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.parts'"
    count = text.count(with_manual)
    if count != 2:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 2 standaardrollen met handleidingen, gevonden {count}')
    text = text.replace(with_manual, without_manual, 2)
    text += '\n' + MARKER + '\n'
    PATH.write_text(text, encoding='utf-8')

print('[Machinepark] rechtenbasis voorbereid voor complete Synology/Netlify catalog')
