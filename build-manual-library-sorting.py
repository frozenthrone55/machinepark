from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLIENT = ROOT / 'manual-library.js'

if not CLIENT.exists():
    raise SystemExit('Buildvalidatie mislukt: manual-library.js ontbreekt voor sorteerfix')

source = CLIENT.read_text(encoding='utf-8')
MARKER = '// machinepark-manual-library-sorting-v1'

old_helpers = '''  function optionValues(values) {
    return [...new Set(values.map((item) => String(item || '').trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'nl-BE', { numeric: true, sensitivity: 'base' }));
  }

  function fillSelect(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` + optionValues(values).map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }
'''

new_helpers = '''  // machinepark-manual-library-sorting-v1
  function manualCompareText(a, b) {
    return String(a || '').localeCompare(String(b || ''), 'nl-BE', { numeric: true, sensitivity: 'base' });
  }

  function manualValueEquals(a, b) {
    return manualNorm(a) === manualNorm(b);
  }

  function optionValues(values) {
    const unique = new Map();
    values.map((item) => String(item || '').trim()).filter(Boolean).forEach((value) => {
      const key = manualNorm(value);
      if (key && !unique.has(key)) unique.set(key, value);
    });
    return [...unique.values()].sort(manualCompareText);
  }

  function fillSelect(select, values, emptyLabel) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = `<option value="">${esc(emptyLabel)}</option>` + optionValues(values).map((value) => `<option value="${esc(value)}">${esc(value)}</option>`).join('');
    const matching = [...select.options].find((option) => option.value && manualValueEquals(option.value, current));
    select.value = matching?.value || '';
  }
'''

if MARKER not in source:
    if source.count(old_helpers) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: helpers voor handleidingfilters niet uniek gevonden ({source.count(old_helpers)}x)')
    source = source.replace(old_helpers, new_helpers, 1)

old_model_filter = "fillSelect(modelFilter, manualLibrary.filter((manual) => !selectedBrand || manual.brand === selectedBrand).map((manual) => manual.model), 'Alle modellen');"
new_model_filter = "fillSelect(modelFilter, manualLibrary.filter((manual) => !selectedBrand || manualValueEquals(manual.brand, selectedBrand)).map((manual) => manual.model), 'Alle modellen');"
if old_model_filter in source:
    source = source.replace(old_model_filter, new_model_filter, 1)
elif new_model_filter not in source:
    raise SystemExit('Buildvalidatie mislukt: model-filter van handleidingen niet gevonden')

old_filter_block = '''      if (selectedBrand && manual.brand !== selectedBrand) return false;
      if (selectedModel && manual.model !== selectedModel) return false;
      if (selectedType && manual.type !== selectedType) return false;'''
new_filter_block = '''      if (selectedBrand && !manualValueEquals(manual.brand, selectedBrand)) return false;
      if (selectedModel && !manualValueEquals(manual.model, selectedModel)) return false;
      if (selectedType && !manualValueEquals(manual.type, selectedType)) return false;'''
if old_filter_block in source:
    source = source.replace(old_filter_block, new_filter_block, 1)
elif new_filter_block not in source:
    raise SystemExit('Buildvalidatie mislukt: actieve handleidingfilters niet gevonden')

old_sort = ".sort((a, b) => manualSpecificity(a) - manualSpecificity(b) || String(a.brand || '').localeCompare(String(b.brand || ''), 'nl-BE') || String(a.model || '').localeCompare(String(b.model || ''), 'nl-BE') || String(a.title || '').localeCompare(String(b.title || ''), 'nl-BE'));"
new_sort = ".sort((a, b) => manualCompareText(a.title, b.title) || manualCompareText(a.brand, b.brand) || manualCompareText(a.model, b.model) || manualCompareText(a.type, b.type) || manualCompareText(manualScopeText(a), manualScopeText(b)) || manualCompareText(a.id, b.id));"
if old_sort in source:
    source = source.replace(old_sort, new_sort, 1)
elif new_sort not in source:
    raise SystemExit('Buildvalidatie mislukt: tabelsortering van handleidingen niet gevonden')

CLIENT.write_text(source, encoding='utf-8')

built = CLIENT.read_text(encoding='utf-8')
required = [
    MARKER,
    'function manualCompareText(a, b)',
    'function manualValueEquals(a, b)',
    'const unique = new Map()',
    'manualValueEquals(manual.brand, selectedBrand)',
    'manualCompareText(a.title, b.title)',
    'manualCompareText(a.brand, b.brand)',
    'manualCompareText(a.model, b.model)',
    'manualCompareText(a.type, b.type)',
]
missing = [needle for needle in required if needle not in built]
if missing:
    raise SystemExit('Buildvalidatie handleiding-sortering mislukt: ' + ', '.join(missing))

print('[Machinepark] handleidingen alfabetisch op titel gesorteerd; merk, model en type zijn stabiele vervolgsleutels')
