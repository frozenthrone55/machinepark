from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
SCRIPT_START = '<script ' + 'data-machinepark-' + 'build-fix="work-orders-v1">'

# De werkbonpatch wordt na de printpatches gebouwd. Die bevatten zelf HTML-strings
# met </body>; verplaats daarom het featureblok expliciet naar de echte document-body.
start = index.find(SCRIPT_START)
if start < 0:
    raise SystemExit('Buildvalidatie mislukt: werkbonscript niet gevonden voor veilige plaatsing')
end = index.find('</script>', start)
if end < 0:
    raise SystemExit('Buildvalidatie mislukt: werkbonscript heeft geen afsluitende script-tag')
end += len('</script>')
block = index[start:end]
index = index[:start] + index[end:]

# Vermijd een extra wrapper op applyOperationalPermissions. Werkbonkaart-rechten
# volgen rechtstreeks de centrale rol-update; zo blijft de kernfunctie slechts
# door de bestaande rollenmodules omwikkeld.
old_access_hook = """  const baseApplyOperationalPermissionsForWorkOrders = applyOperationalPermissions;
  applyOperationalPermissions = function() {
    baseApplyOperationalPermissionsForWorkOrders();
    ensureSettingsCard();
  };
  window.applyOperationalPermissions = applyOperationalPermissions;

"""
new_access_hook = """  const baseApplyServerAccessForWorkOrders = window.applyMachineparkServerAccess;
  if (typeof baseApplyServerAccessForWorkOrders === 'function') {
    window.applyMachineparkServerAccess = function(body) {
      const result = baseApplyServerAccessForWorkOrders(body);
      setTimeout(() => ensureSettingsCard(), 0);
      return result;
    };
  }

"""
if old_access_hook not in block:
    raise SystemExit('Buildvalidatie mislukt: oude werkbonrechten-wrapper niet gevonden')
block = block.replace(old_access_hook, new_access_hook, 1)

body_pos = index.rfind('</body>')
if body_pos < 0:
    raise SystemExit('Buildvalidatie mislukt: echte </body> ontbreekt voor werkbonscript')
index = index[:body_pos] + block + '\n' + index[body_pos:]
index_path.write_text(index, encoding='utf-8')

if index.rfind(SCRIPT_START) < index.rfind('</head>'):
    raise SystemExit('Buildvalidatie mislukt: werkbonscript staat niet in document-body')
if 'baseApplyOperationalPermissionsForWorkOrders' in index:
    raise SystemExit('Buildvalidatie mislukt: dubbele operationele rechtenwrapper is blijven staan')

print('[Machinepark] werkbonmodule veilig geplaatst zonder extra kernwrapper')
