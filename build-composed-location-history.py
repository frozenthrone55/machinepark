from pathlib import Path
ROOT = Path(__file__).resolve().parent
p = ROOT / 'index.html'
s = p.read_text()
marker = 'data-machinepark-build-fix="composed-location-history-v1"'
if marker not in s:
    js = (ROOT / 'composed-location-history.js').read_text()
    anchor = '  function openComposedPreview(doc)'
    if s.count(anchor) != 1: raise SystemExit('Locatiehistoriek: preview-anker ontbreekt')
    s = s.replace(anchor, js + '\n' + anchor, 1)
    s = s.replace('</head>', '<meta ' + marker + '>\n</head>', 1)
    p.write_text(s)
print('[Machinepark] samengestelde locatiehistoriek toegevoegd')
