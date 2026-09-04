from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parent
permissions_path = ROOT / 'netlify/functions/_shared/permissions.mjs'
endpoint_path = ROOT / 'netlify/functions/manual-library.mjs'
manual_path = ROOT / 'manual-library.js'
index_path = ROOT / 'index.html'
sw_path = ROOT / 'sw.js'

for path in (permissions_path, endpoint_path, manual_path, index_path, sw_path):
    if not path.exists():
        raise SystemExit(f'Buildvalidatie mislukt: {path.name} ontbreekt voor native handleidingensync')

# 1. Handleidingen zijn echte Machinepark-rechten, net als Storingen.
permissions = permissions_path.read_text(encoding='utf-8')
PERM_MARKER = '// machinepark-manual-native-permissions-v1'
if PERM_MARKER not in permissions:
    view_anchor = "  { group: 'Weergave', key: 'view.faults', label: 'Storingen bekijken' },\n"
    if permissions.count(view_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: rechtenanker view.faults niet uniek')
    permissions = permissions.replace(
        view_anchor,
        view_anchor + "  { group: 'Weergave', key: 'view.manuals', label: 'Handleidingen bekijken' },\n",
        1,
    )

    manage_anchor = "  { group: 'Storingen', key: 'faults.manage', label: 'Storingsbibliotheek beheren' },\n"
    if permissions.count(manage_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: rechtenanker faults.manage niet uniek')
    permissions = permissions.replace(
        manage_anchor,
        manage_anchor + "  { group: 'Handleidingen', key: 'manuals.manage', label: 'Handleidingen beheren' },\n",
        1,
    )

    gebruiker_old = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.parts'"
    gebruiker_new = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts'"
    if permissions.count(gebruiker_old) < 1:
        raise SystemExit('Buildvalidatie mislukt: ingebouwde gebruikersrechten niet gevonden')
    permissions = permissions.replace(gebruiker_old, gebruiker_new, 1)

    technieker_old = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.parts'"
    technieker_new = "'view.dashboard','view.devices','view.maintenance','view.breakdowns','view.faults','view.manuals','view.parts'"
    if permissions.count(technieker_old) < 1:
        raise SystemExit('Buildvalidatie mislukt: ingebouwde techniekerrechten niet gevonden')
    permissions = permissions.replace(technieker_old, technieker_new, 1)

    permissions = permissions.replace(
        "export const PERMISSION_CATALOG = [\n",
        PERM_MARKER + "\nexport const PERMISSION_CATALOG = [\n",
        1,
    )
    permissions_path.write_text(permissions, encoding='utf-8')

# 2. De handleidingenfunctie gebruikt die echte rechten server-side.
endpoint = endpoint_path.read_text(encoding='utf-8')
ENDPOINT_MARKER = '// machinepark-manual-native-access-v1'
if ENDPOINT_MARKER not in endpoint:
    old_read = "function canRead(access) {\n  return Boolean(\n    access?.owner ||\n    access?.permissions?.['view.devices'] ||\n    access?.permissions?.['view.breakdowns'] ||\n    access?.permissions?.['view.settings']\n  );\n}"
    new_read = ENDPOINT_MARKER + "\nfunction canRead(access) {\n  return Boolean(access?.owner || access?.permissions?.['view.manuals']);\n}"
    if endpoint.count(old_read) != 1:
        raise SystemExit('Buildvalidatie mislukt: oude handleidingen-leesrechten niet uniek')
    endpoint = endpoint.replace(old_read, new_read, 1)

    old_manage = "function canManage(access) {\n  return Boolean(access?.owner || access?.permissions?.['view.settings']);\n}"
    new_manage = "function canManage(access) {\n  return Boolean(access?.owner || access?.permissions?.['manuals.manage']);\n}"
    if endpoint.count(old_manage) != 1:
        raise SystemExit('Buildvalidatie mislukt: oude handleidingen-beheerrechten niet uniek')
    endpoint = endpoint.replace(old_manage, new_manage, 1)
    endpoint_path.write_text(endpoint, encoding='utf-8')

# 3. De client behandelt serverrechten als waarheid en ververst online altijd centraal,
#    identiek aan de storingsbibliotheek. Offline blijft de lokale cache beschikbaar.
manual = manual_path.read_text(encoding='utf-8')
CLIENT_MARKER = '// machinepark-manual-native-sync-v1'
if CLIENT_MARKER not in manual:
    derived_old = "  function derivedManualPermissions(permissions = {}) {\n    return {\n      'view.manuals': Boolean(permissions['view.devices'] || permissions['view.breakdowns'] || permissions['view.settings']),\n      'manuals.manage': Boolean(permissions['view.settings']),\n    };\n  }"
    derived_new = CLIENT_MARKER + "\n  function derivedManualPermissions(permissions = {}) {\n    const hasView = Object.prototype.hasOwnProperty.call(permissions, 'view.manuals');\n    const hasManage = Object.prototype.hasOwnProperty.call(permissions, 'manuals.manage');\n    return {\n      'view.manuals': hasView ? Boolean(permissions['view.manuals']) : Boolean(permissions['view.devices'] || permissions['view.breakdowns'] || permissions['view.settings']),\n      'manuals.manage': hasManage ? Boolean(permissions['manuals.manage']) : Boolean(permissions['view.settings']),\n    };\n  }"
    if manual.count(derived_old) != 1:
        raise SystemExit('Buildvalidatie mislukt: afgeleide handleidingenrechten niet uniek')
    manual = manual.replace(derived_old, derived_new, 1)

    early_old = "    if (!force && manualLibraryLoaded) return manualLibrary;"
    early_new = "    if (!force && manualLibraryLoaded && navigator.onLine === false) return manualLibrary;"
    if manual.count(early_old) != 1:
        raise SystemExit('Buildvalidatie mislukt: handleidingencache early-return niet uniek')
    manual = manual.replace(early_old, early_new, 1)

    init_anchor = "  function initManualFeature() {"
    reconnect = "  window.addEventListener('online', () => {\n    if (!canViewManuals()) return;\n    loadManualLibrary(true).then(() => {\n      if (state.view === 'manuals') renderManualLibrary();\n    }).catch(() => {});\n  });\n\n"
    if manual.count(init_anchor) != 1:
        raise SystemExit('Buildvalidatie mislukt: handleidingen init-anker niet uniek')
    manual = manual.replace(init_anchor, reconnect + init_anchor, 1)
    manual_path.write_text(manual, encoding='utf-8')

# 4. De algemene rollenlaag kent Handleidingen als normaal scherm.
index = index_path.read_text(encoding='utf-8')
old_order = "return ['dashboard','devices','maintenance','breakdowns','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';"
new_order = "return ['dashboard','devices','maintenance','breakdowns','faults','manuals','parts','settings'].find((view) => hasPermission(viewPermission(view))) || 'dashboard';"
if old_order in index:
    index = index.replace(old_order, new_order, 1)
elif new_order not in index:
    raise SystemExit('Buildvalidatie mislukt: toegestane schermvolgorde niet gevonden')

# 5. Cache-busting voor de losse handleidingenruntime. Hierdoor kan een oude PWA
#    niet de vorige handleidingenlogica blijven serveren.
manual = manual_path.read_text(encoding='utf-8')
manual_hash = hashlib.sha256(manual.encode('utf-8')).hexdigest()[:12]
manual_url = f'/manual-library.js?v={manual_hash}'
index, loader_count = re.subn(
    r'<script src="/manual-library\.js(?:\?v=[^"]*)?" data-machinepark-manual-library="js"></script>',
    f'<script src="{manual_url}" data-machinepark-manual-library="js"></script>',
    index,
    count=1,
)
if loader_count != 1:
    raise SystemExit('Buildvalidatie mislukt: handleidingenruntime-loader niet uniek')
index_path.write_text(index, encoding='utf-8')

sw = sw_path.read_text(encoding='utf-8')
sw, sw_count = re.subn(
    r"'/manual-library\.js(?:\?v=[^']*)?'",
    f"'{manual_url}'",
    sw,
    count=1,
)
if sw_count != 1:
    raise SystemExit('Buildvalidatie mislukt: handleidingenruntime ontbreekt in service worker')
sw_path.write_text(sw, encoding='utf-8')

# Eindvalidatie.
permissions = permissions_path.read_text(encoding='utf-8')
endpoint = endpoint_path.read_text(encoding='utf-8')
manual = manual_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
required = [
    (permissions, "key: 'view.manuals'"),
    (permissions, "key: 'manuals.manage'"),
    (permissions, "'view.faults','view.manuals','view.parts'"),
    (endpoint, "access?.permissions?.['view.manuals']"),
    (endpoint, "access?.permissions?.['manuals.manage']"),
    (manual, "manualLibraryLoaded && navigator.onLine === false"),
    (manual, "window.addEventListener('online'"),
    (index, "'faults','manuals','parts'"),
    (index, manual_url),
    (sw, manual_url),
]
missing = [needle for haystack, needle in required if needle not in haystack]
if missing:
    raise SystemExit('Buildvalidatie native handleidingensync mislukt: ' + ', '.join(missing))

print(f'[Machinepark] handleidingen gebruiken native rechten, centrale live-sync en cache-busting ({manual_hash})')
