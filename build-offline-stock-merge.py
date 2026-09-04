from pathlib import Path

ROOT = Path(__file__).resolve().parent
path = ROOT / 'offline-first.js'
source = path.read_text(encoding='utf-8')
MARKER = '// machinepark-offline-stock-delta-merge-v1'


def replace_once(old, new, label):
    global source
    count = source.count(old)
    if count != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x')
    source = source.replace(old, new, 1)


if MARKER not in source:
    replace_once(
        '  function mergeEntity(base, local, remote, stats) {',
        f'''  {MARKER}\n  function mergeEntity(base, local, remote, stats, storeName = '') {{''',
        'mergeEntity context',
    )
    replace_once(
        "      const remoteChanged = rHas !== bHas || !sameValue(r, b);\n\n      if (!localChanged && remoteChanged) {",
        """      const remoteChanged = rHas !== bHas || !sameValue(r, b);\n\n      // Voorraad is een teller. Als offline en online sinds dezelfde basis allebei\n      // voorraad wijzigen, moeten beide delta's worden toegepast in plaats van\n      // één absolute voorraadwaarde te laten winnen.\n      if (storeName === 'parts' && key === 'stock' && localChanged && remoteChanged && bHas && lHas && rHas) {\n        const baseStock = Number(b), localStock = Number(l), remoteStock = Number(r);\n        if ([baseStock, localStock, remoteStock].every(Number.isFinite)) {\n          result[key] = baseStock + (localStock - baseStock) + (remoteStock - baseStock);\n          continue;\n        }\n      }\n\n      if (!localChanged && remoteChanged) {""",
        'voorraaddelta merge',
    )
    replace_once(
        '  function mergeStore(baseList, localList, remoteList, stats) {',
        "  function mergeStore(baseList, localList, remoteList, stats, storeName = '') {",
        'mergeStore context',
    )
    replace_once(
        '      const item = mergeEntity(base.get(id), local.get(id), remote.get(id), stats);',
        '      const item = mergeEntity(base.get(id), local.get(id), remote.get(id), stats, storeName);',
        'mergeEntity storeName doorgeven',
    )
    replace_once(
        '    for (const storeName of stores) merged[storeName] = mergeStore(base?.[storeName], local?.[storeName], remote?.[storeName], stats);',
        '    for (const storeName of stores) merged[storeName] = mergeStore(base?.[storeName], local?.[storeName], remote?.[storeName], stats, storeName);',
        'mergeStore storeName doorgeven',
    )
    path.write_text(source, encoding='utf-8')

for needle in [
    MARKER,
    "storeName === 'parts' && key === 'stock'",
    'baseStock + (localStock - baseStock) + (remoteStock - baseStock)',
    "mergeStore(baseList, localList, remoteList, stats, storeName = '')",
    'mergeEntity(base.get(id), local.get(id), remote.get(id), stats, storeName)',
]:
    if needle not in source:
        raise SystemExit(f'Buildvalidatie mislukt: offline voorraadmerge ontbreekt ({needle})')

print('[Machinepark] gelijktijdige offline/online voorraadmutaties worden als delta’s samengevoegd')
