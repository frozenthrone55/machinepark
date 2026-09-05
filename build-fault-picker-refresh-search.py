from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'fault-library.js'
source = path.read_text(encoding='utf-8')
MARKER = '// machinepark-fault-picker-refresh-search-v1'

old_search = """  function faultSearchText(fault) {
    return faultNorm([
      fault?.code, fault?.name, fault?.category, fault?.brand, fault?.model,
      fault?.description, ...(fault?.symptoms || []), ...(fault?.causes || []),
      ...(fault?.solutions || []), fault?.notes,
    ].filter(Boolean).join(' '));
  }
"""

new_search = """  // machinepark-fault-picker-refresh-search-v1
  function faultSearchText(fault) {
    return faultNorm([
      fault?.code, fault?.name, fault?.category, fault?.brand, fault?.model,
      fault?.description, ...(fault?.symptoms || []), ...(fault?.causes || []),
      ...(fault?.solutions || []), fault?.notes,
    ].filter(Boolean).join(' '));
  }

  function faultCompact(value) {
    return faultNorm(value).replace(/[^a-z0-9]+/g, '');
  }

  function faultMatchesQuery(fault, query) {
    const q = faultNorm(query);
    if (!q) return true;
    const text = faultSearchText(fault);
    if (text.includes(q)) return true;
    const compactQuery = faultCompact(q);
    return Boolean(compactQuery && faultCompact(text).includes(compactQuery));
  }
"""

if MARKER not in source:
    if source.count(old_search) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 faultSearchText, gevonden {source.count(old_search)}')
    source = source.replace(old_search, new_search, 1)

    old_candidate = "const candidates = faultLibrary.filter((fault) => fault.active !== false && (!q || faultSearchText(fault).includes(q)));"
    new_candidate = "const candidates = faultLibrary.filter((fault) => fault.active !== false && faultMatchesQuery(fault, q));"
    if source.count(old_candidate) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1 kandidaatfilter, gevonden {source.count(old_candidate)}')
    source = source.replace(old_candidate, new_candidate, 1)

    # Bij openen altijd eerst een actuele online versie ophalen. Als dat mislukt,
    # behoudt loadFaultLibrary de reeds geladen/offline bibliotheek.
    source = source.replace("await loadFaultLibrary();\n      const deviceId", "await loadFaultLibrary(true);\n      const deviceId", 1)
    source = source.replace("await loadFaultLibrary();\n          input.focus();", "await loadFaultLibrary(true);\n          input.focus();", 1)
    path.write_text(source, encoding='utf-8')

built = path.read_text(encoding='utf-8')
for needle in [
    MARKER,
    'function faultCompact',
    'function faultMatchesQuery',
    'faultCompact(text).includes(compactQuery)',
    'fault.active !== false && faultMatchesQuery(fault, q)',
    'await loadFaultLibrary(true);',
]:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: storingspicker-refresh ontbreekt ({needle})')

if built.count('await loadFaultLibrary(true);') < 2:
    raise SystemExit('Buildvalidatie mislukt: niet alle storingspickers verversen centraal')

print('[Machinepark] storingspicker ververst centraal en zoekt tolerant op schrijfvarianten')
