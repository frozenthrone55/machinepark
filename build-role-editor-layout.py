from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / "index.html"
index = index_path.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="role-editor-layout-v1"'


def replace_once(old, new, label):
    global index
    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: verwacht 1x {label}, gevonden {count}x")
    index = index.replace(old, new, 1)


if MARKER not in index:
    old_permission_html = '''const permissionHtml = groups.map(([group, items]) => `<div class="role-permission-group"><div class="role-permission-group-title">${esc(group)}</div><div class="role-permission-list">${items.map((item) => `<label class="role-permission-item"><input type="checkbox" name="perm:${esc(item.key)}" ${existing?.permissions?.[item.key] ? 'checked' : ''}><span>${esc(item.label)}</span></label>`).join('')}</div></div>`).join('');'''
    new_permission_html = '''const permissionHtml = groups.map(([group, items]) => `<section class="role-editor-group"><div class="role-editor-group-head"><div><h4>${esc(group)}</h4><small>${items.length} ${items.length === 1 ? 'recht' : 'rechten'}</small></div></div><div class="role-editor-rights">${items.map((item) => `<label class="role-editor-right"><span class="role-editor-right-label">${esc(item.label)}</span><input class="role-editor-switch" type="checkbox" name="perm:${esc(item.key)}" ${existing?.permissions?.[item.key] ? 'checked' : ''} aria-label="${esc(item.label)}"></label>`).join('')}</div></section>`).join('');'''
    replace_once(old_permission_html, new_permission_html, 'rechtenlijst rollen-editor')

    old_body = '''const body = `<div class="form-grid">${nameField}<div class="field full"><div class="alert"><strong>Veiligheidsregel</strong>De vaste hoofdbeheerder behoudt altijd alle rechten, ongeacht deze schakelaars.</div></div><div class="field full role-permission-groups">${permissionHtml}</div></div>`;'''
    new_body = '''const body = `<div class="role-editor-layout"><div class="role-editor-top"><div class="role-editor-name-card">${nameField}</div><div class="role-editor-safety-card"><div class="role-editor-safety-icon">✓</div><div><strong>Veiligheidsregel</strong><p>De vaste hoofdbeheerder behoudt altijd alle rechten, ongeacht deze instellingen.</p></div></div></div><div class="role-editor-section-head"><div><strong>Rechten per onderdeel</strong><span>Zet per handeling de schakelaar aan of uit.</span></div></div><div class="role-editor-groups">${permissionHtml}</div></div>`;'''
    replace_once(old_body, new_body, 'opmaak rollen-editor')

    style = f'''
<style {MARKER}>
.modal:has(.role-editor-layout){{width:min(1120px,calc(100vw - 34px))}}
.role-editor-layout{{display:grid;gap:18px}}
.role-editor-top{{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.85fr);gap:14px;align-items:stretch}}
.role-editor-name-card,.role-editor-safety-card{{border:1px solid var(--line);border-radius:14px;padding:16px;background:#fbfcfb}}
.role-editor-name-card{{display:flex;align-items:center}}
.role-editor-name-card .field{{width:100%}}
.role-editor-name-card .field label{{font-size:12px;text-transform:uppercase;letter-spacing:.035em;color:#68756f}}
.role-editor-name-card .field input{{font-size:15px;font-weight:700;padding:11px 12px;background:#fff}}
.role-editor-safety-card{{display:grid;grid-template-columns:36px 1fr;gap:12px;align-content:center;background:#f5f9f7;border-color:#d6e5df}}
.role-editor-safety-icon{{width:36px;height:36px;border-radius:11px;background:#e2f1ea;color:var(--success);display:grid;place-items:center;font-weight:900;font-size:17px}}
.role-editor-safety-card strong{{display:block;font-size:13px;margin:1px 0 4px}}
.role-editor-safety-card p{{margin:0;color:var(--muted);font-size:12px;line-height:1.45}}
.role-editor-section-head{{display:flex;justify-content:space-between;align-items:end;gap:12px;padding:2px 1px 0}}
.role-editor-section-head strong{{display:block;font-size:15px}}
.role-editor-section-head span{{display:block;margin-top:3px;color:var(--muted);font-size:12px}}
.role-editor-groups{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;align-items:start}}
.role-editor-group{{border:1px solid var(--line);border-radius:14px;background:#fff;overflow:hidden;box-shadow:0 5px 16px rgba(25,57,48,.035)}}
.role-editor-group-head{{display:flex;justify-content:space-between;align-items:center;min-height:54px;padding:12px 15px;background:#f7faf8;border-bottom:1px solid var(--line)}}
.role-editor-group-head h4{{margin:0;font-size:13px;color:#31413b}}
.role-editor-group-head small{{display:block;margin-top:2px;color:var(--muted);font-size:10.5px}}
.role-editor-rights{{display:grid}}
.role-editor-right{{display:grid;grid-template-columns:minmax(0,1fr) 42px;align-items:center;gap:16px;min-height:49px;padding:10px 14px;border-bottom:1px solid #edf1ef;cursor:pointer;transition:background .15s ease}}
.role-editor-right:last-child{{border-bottom:0}}
.role-editor-right:hover{{background:#fbfcfb}}
.role-editor-right-label{{font-size:12.5px;line-height:1.35;color:#34433d;padding-right:4px}}
.role-editor-switch{{appearance:none;-webkit-appearance:none;width:40px;height:22px;margin:0;justify-self:end;border:0;border-radius:999px;background:#d9e0dd;position:relative;cursor:pointer;outline:none;transition:background .18s ease,box-shadow .18s ease}}
.role-editor-switch::after{{content:"";position:absolute;width:18px;height:18px;left:2px;top:2px;border-radius:50%;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.2);transition:transform .18s ease}}
.role-editor-switch:checked{{background:var(--brand2)}}
.role-editor-switch:checked::after{{transform:translateX(18px)}}
.role-editor-switch:focus-visible{{box-shadow:0 0 0 3px rgba(44,106,88,.18)}}
@media(max-width:860px){{
  .role-editor-top,.role-editor-groups{{grid-template-columns:1fr}}
  .modal:has(.role-editor-layout){{width:min(760px,calc(100vw - 28px))}}
}}
@media(max-width:700px){{
  .modal:has(.role-editor-layout){{width:100%}}
  .role-editor-layout{{gap:14px}}
  .role-editor-top{{gap:10px}}
  .role-editor-name-card,.role-editor-safety-card{{padding:13px}}
  .role-editor-group-head{{min-height:50px;padding:11px 13px}}
  .role-editor-right{{min-height:48px;padding:10px 12px;gap:12px}}
  .role-editor-right-label{{font-size:12px}}
}}
</style>
'''
    replace_once('</head>', style + '</head>', 'role-editor stylesheet')

    index_path.write_text(index, encoding="utf-8")
    print('[Machinepark] rollen-editor netjes uitgelijnd en responsief')
else:
    print('[Machinepark] rollen-editor layout reeds actief')
