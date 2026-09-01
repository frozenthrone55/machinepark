from pathlib import Path

ROOT = Path(__file__).resolve().parent
client_path = ROOT / 'manual-library.js'
client = client_path.read_text(encoding='utf-8')

MARKER = '// machinepark-manual-device-brand-aliases-v1'

old = '''  function manualAppliesToDevice(manual, device) {
    if (!manual || !device || manual.active === false) return false;
    if (manual.deviceId) return manual.deviceId === device.id;
    if (!manual.brand) return true;
    const brandNeedle = manualNorm(manual.brand);
    const deviceBrand = manualNorm([device.brand, device.model].filter(Boolean).join(' '));
    if (!brandNeedle || !(deviceBrand.includes(brandNeedle) || brandNeedle.includes(deviceBrand))) return false;
    if (!manual.model) return true;
    const modelNeedle = manualNorm(manual.model);
    const deviceModel = manualNorm([device.model, device.brand].filter(Boolean).join(' '));
    return Boolean(modelNeedle && (deviceModel.includes(modelNeedle) || modelNeedle.includes(deviceModel)));
  }
'''

new = '''  // machinepark-manual-device-brand-aliases-v1
  const MANUAL_BRAND_MODEL_HINTS = {
    bravilor: ['sego', 'bolero', 'esprecious', 'sprso'],
  };

  function manualBrandFamily(value) {
    const normalized = manualNorm(value);
    if (normalized.includes('bravilor') || normalized.includes('bonamat')) return 'bravilor';
    return normalized;
  }

  function manualIdentityMatches(haystack, needle) {
    const text = manualNorm(haystack);
    const wanted = manualNorm(needle);
    return Boolean(wanted && (text.includes(wanted) || wanted.includes(text)));
  }

  function manualAppliesToDevice(manual, device) {
    if (!manual || !device || manual.active === false) return false;
    if (manual.deviceId) return manual.deviceId === device.id;
    if (!manual.brand) return true;

    const deviceIdentity = manualNorm([device.brand, device.model].filter(Boolean).join(' '));
    const brandNeedle = manualNorm(manual.brand);
    const brandFamily = manualBrandFamily(brandNeedle);
    const modelNeedle = manualNorm(manual.model);
    const directBrandMatch = manualIdentityMatches(deviceIdentity, brandNeedle);
    const hintedBrandMatch = (MANUAL_BRAND_MODEL_HINTS[brandFamily] || [])
      .some((hint) => manualIdentityMatches(deviceIdentity, hint));
    const brandMatch = directBrandMatch || hintedBrandMatch;
    const modelMatch = !modelNeedle || manualIdentityMatches(deviceIdentity, modelNeedle);

    if (brandMatch && modelMatch) return true;

    // Sommige inventarisregels bevatten alleen de modelnaam (bv. "Sego") in
    // het merkveld. Een voldoende specifieke modelmatch mag dan de ontbrekende
    // fabrikantnaam opvangen, maar een ander model blijft uitgesloten.
    if (!brandMatch && modelNeedle.length >= 4 && modelMatch) return true;
    return false;
  }
'''

if MARKER not in client:
    if client.count(old) != 1:
        raise SystemExit('Buildvalidatie mislukt: bestaande handleiding-toestelmatch niet uniek gevonden')
    client = client.replace(old, new, 1)
    client_path.write_text(client, encoding='utf-8')

built = client_path.read_text(encoding='utf-8')
required = [
    MARKER,
    "bravilor: ['sego', 'bolero', 'esprecious', 'sprso']",
    "normalized.includes('bravilor') || normalized.includes('bonamat')",
    'const hintedBrandMatch',
    'modelNeedle.length >= 4 && modelMatch',
]
missing = [needle for needle in required if needle not in built]
if missing:
    raise SystemExit('Buildvalidatie slimme handleidingkoppeling mislukt: ' + ', '.join(missing))

if 'if (!brandNeedle || !(deviceBrand.includes(brandNeedle)' in built:
    raise SystemExit('Buildvalidatie mislukt: oude strikte merkblokkade is nog actief')

print('[Machinepark] handleidingen herkennen model-only toestellen zoals Sego als Bravilor')
