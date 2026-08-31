from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    index = index.replace(old, new, 1)


# HTML number-inputs gedragen zich per browser/locale verschillend en blokkeren
# vaak een komma als decimaalteken. Gebruik voor werkbon-getallen daarom een
# tekstinput met een decimaal toetsenbord en valideer de invoer zelf.
old_input = """    const type = field.type === 'number' ? 'number' : field.type === 'date' ? 'date' : 'text';
    return `<div class=\"workorder-maintenance-field\"><label for=\"${esc(id)}\">${esc(field.label)}${required}</label><input id=\"${esc(id)}\" type=\"${type}\" data-workorder-field=\"${esc(field.id)}\" value=\"${esc(value ?? '')}\"></div>`;
"""
new_input = """    if (field.type === 'number') {
      return `<div class=\"workorder-maintenance-field\"><label for=\"${esc(id)}\">${esc(field.label)}${required}</label><input id=\"${esc(id)}\" type=\"text\" inputmode=\"decimal\" autocomplete=\"off\" data-workorder-number=\"1\" data-workorder-field=\"${esc(field.id)}\" value=\"${esc(value ?? '')}\" placeholder=\"bv. 12,5\"></div>`;
    }
    const type = field.type === 'date' ? 'date' : 'text';
    return `<div class=\"workorder-maintenance-field\"><label for=\"${esc(id)}\">${esc(field.label)}${required}</label><input id=\"${esc(id)}\" type=\"${type}\" data-workorder-field=\"${esc(field.id)}\" value=\"${esc(value ?? '')}\"></div>`;
"""
replace_once(old_input, new_input, 'decimale werkboninvoer')

old_value = """      const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
      if (field.required && (field.type === 'checkbox' ? !value : !String(value).trim())) {
"""
new_value = """      const value = field.type === 'checkbox' ? Boolean(input?.checked) : String(input?.value ?? '').trim();
      if (field.type === 'number' && value !== '' && !/^[+-]?(?:\\d+(?:[.,]\\d+)?|[.,]\\d+)$/.test(value)) {
        throw new Error(`Gebruik een geldig getal bij “${field.label}”, bijvoorbeeld 12,5 of 12.5.`);
      }
      if (field.required && (field.type === 'checkbox' ? !value : !String(value).trim())) {
"""
replace_once(old_value, new_value, 'validatie decimale werkboninvoer')

index_path.write_text(index, encoding='utf-8')

for needle in [
    'data-workorder-number=\"1\"',
    'inputmode=\"decimal\"',
    'bij “${field.label}”, bijvoorbeeld 12,5 of 12.5',
]:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: decimale werkbonfunctie ontbreekt: {needle}')

if "field.type === 'number' ? 'number'" in index:
    raise SystemExit('Buildvalidatie mislukt: beperkende HTML number-input is nog actief voor werkbonnen')

print('[Machinepark] werkbon-getalvelden accepteren komma en punt als decimaalteken')
