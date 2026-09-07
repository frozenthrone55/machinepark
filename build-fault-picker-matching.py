from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'fault-library.js'
source = path.read_text(encoding='utf-8')
MARKER = '// machinepark-fault-picker-matching-v2'

old_scope = """  function faultAppliesToDevice(fault, device) {
    if (!fault?.brand) return true;
    const brandNeedle = faultNorm(fault.brand);
    const deviceBrand = faultNorm([device?.brand, device?.model].filter(Boolean).join(' '));
    if (!brandNeedle || !(deviceBrand.includes(brandNeedle) || brandNeedle.includes(deviceBrand))) return false;
    if (!fault?.model) return true;
    const modelNeedle = faultNorm(fault.model);
    const deviceModel = faultNorm([device?.model, device?.brand].filter(Boolean).join(' '));
    return Boolean(modelNeedle && (deviceModel.includes(modelNeedle) || modelNeedle.includes(deviceModel)));
  }
"""

new_scope = """  // machinepark-fault-picker-matching-v2
  function faultScopeComparable(value) {
    return faultNorm(value)
      .replace(/\\([^)]*\\)/g, ' ')
      .replace(/[^a-z0-9]+/g, ' ')
      .replace(/\\s+/g, ' ')
      .trim();
  }

  function faultScopeMatches(needleValue, targetValue) {
    const needle = faultScopeComparable(needleValue);
    const target = faultScopeComparable(targetValue);
    if (!needle) return true;
    if (!target) return false;
    if (needle === target || target.includes(needle) || needle.includes(target)) return true;
    const needleTokens = needle.split(' ').filter((token) => token.length > 1);
    const targetTokens = target.split(' ').filter((token) => token.length > 1);
    if (!needleTokens.length || !targetTokens.length) return false;
    return needleTokens.every((token) => targetTokens.includes(token)) || targetTokens.every((token) => needleTokens.includes(token));
  }

  function faultAppliesToDevice(fault, device) {
    if (!fault?.brand) return true;
    const deviceBrand = String(device?.brand || '');
    const deviceModel = String(device?.model || '');
    const deviceCombined = [deviceBrand, deviceModel].filter(Boolean).join(' ');
    const brandMatches = faultScopeMatches(fault.brand, deviceBrand) || faultScopeMatches(fault.brand, deviceCombined);
    if (!brandMatches) return false;
    if (!fault?.model) return true;
    return faultScopeMatches(fault.model, deviceModel) || faultScopeMatches(fault.model, deviceCombined);
  }
"""

old_matching = """  function matchingFaultsForDevice(device, query = '') {
    const q = faultNorm(query);
    return faultLibrary.filter((fault) => fault.active !== false && faultAppliesToDevice(fault, device) && (!q || faultSearchText(fault).includes(q))).sort((a, b) => faultSpecificity(a) - faultSpecificity(b) || String(a.code || a.name || '').localeCompare(String(b.code || b.name || ''), 'nl-BE', { numeric: true })).slice(0, 12);
  }

  function pickerResultsHtml(device, query) {
    const matches = matchingFaultsForDevice(device, query);
    if (!matches.length) return '<div class=\"global-search-empty\">Geen passende storing gevonden.</div>';
    return matches.map((fault) => `<button type=\"button\" class=\"fault-picker-result\" data-fault-pick=\"${esc(fault.id)}\"><strong>${esc(faultTitle(fault))}</strong><small>${esc(faultScopeText(fault))}${fault.category ? ` · ${esc(fault.category)}` : ''}</small></button>`).join('');
  }
"""

new_matching = """  function matchingFaultsForDevice(device, query = '') {
    const q = faultNorm(query);
    const candidates = faultLibrary.filter((fault) => fault.active !== false && (!q || faultSearchText(fault).includes(q)));
    const visible = q ? candidates : candidates.filter((fault) => faultAppliesToDevice(fault, device));
    return visible.sort((a, b) => {
      const aMismatch = faultAppliesToDevice(a, device) ? 0 : 1;
      const bMismatch = faultAppliesToDevice(b, device) ? 0 : 1;
      return aMismatch - bMismatch || faultSpecificity(a) - faultSpecificity(b) || String(a.code || a.name || '').localeCompare(String(b.code || b.name || ''), 'nl-BE', { numeric: true });
    }).slice(0, 12);
  }

  function pickerResultsHtml(device, query) {
    const matches = matchingFaultsForDevice(device, query);
    if (!matches.length) return '<div class=\"global-search-empty\">Geen passende storing gevonden.</div>';
    return matches.map((fault) => {
      const applies = faultAppliesToDevice(fault, device);
      const mismatch = applies ? '' : ' · ⚠ ander merk/model';
      return `<button type=\"button\" class=\"fault-picker-result\" data-fault-pick=\"${esc(fault.id)}\"><strong>${esc(faultTitle(fault))}</strong><small>${esc(faultScopeText(fault))}${fault.category ? ` · ${esc(fault.category)}` : ''}${mismatch}</small></button>`;
    }).join('');
  }
"""

if MARKER not in source:
    if source.count(old_scope) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 oude toestelmatching, gevonden {source.count(old_scope)}')
    if source.count(old_matching) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 oude storingszoeker, gevonden {source.count(old_matching)}')
    source = source.replace(old_scope, new_scope, 1)
    source = source.replace(old_matching, new_matching, 1)
    path.write_text(source, encoding='utf-8')

built = path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'faultScopeComparable',
    'faultScopeMatches',
    "const visible = q ? candidates : candidates.filter",
    '⚠ ander merk/model',
    'aMismatch - bMismatch',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: verbeterde storingszoeker ontbreekt ({needle})')

print('[Machinepark] storingszoeker toont passende merk/model-resultaten eerst en verbergt tekstmatches niet meer')
