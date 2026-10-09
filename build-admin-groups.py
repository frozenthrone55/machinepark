from pathlib import Path
ROOT = Path(__file__).resolve().parent
path = ROOT / 'index.html'
text = path.read_text()
marker = 'data-machinepark-build-fix="admin-groups-v1"'
if marker not in text:
    css = '''.admin-group-list{display:grid;grid-template-columns:1fr;gap:12px}.admin-group{background:white;border:1px solid var(--line);border-radius:14px}.admin-group>summary{cursor:pointer;padding:18px;list-style-position:inside}.admin-group>summary strong{font-size:16px}.admin-group>summary small{display:block;color:var(--muted);margin:6px 0 0 19px}.admin-group-body{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;padding:0 16px 16px}.admin-group-body>.settings-card{min-width:0}.admin-group[hidden]{display:none}.admin-sync-history{margin-top:14px;border-top:1px solid var(--line);padding-top:12px}.admin-sync-history>summary{cursor:pointer;font-weight:700}@media(max-width:700px){.admin-group-body{grid-template-columns:1fr;padding:0 10px 10px}.admin-group>summary{padding:15px}.admin-group-body>.settings-card{grid-column:1!important}}'''
    text=text.replace('</head>',f'<style {marker}>{css}</style>\n</head>',1)
    pos=text.rfind('</body>')
    if pos < 0: raise SystemExit('Beheer: body ontbreekt')
    script=(ROOT/'admin-groups.js').read_text()
    text=text[:pos]+f'<script {marker}>\n{script}\n</script>\n'+text[pos:]
    path.write_text(text)
print('[Machinepark] Beheer gegroepeerd zonder zoekveld; alle groepen standaard dicht')
