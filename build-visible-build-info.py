from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
package_path = ROOT / 'package.json'

text = index_path.read_text(encoding='utf-8')
package = json.loads(package_path.read_text(encoding='utf-8'))
version = str(package.get('version') or '').strip()
if not version:
    raise SystemExit('Buildvalidatie mislukt: package.json bevat geen versie')

MARKER = 'data-machinepark-build-info="visible-build-info-v1"'
LOCAL_FOOTER = f'<div class="side-foot">Lokale synchronisatie • Synology<br><br>Eigen beheer • lokale opslag<br>v{version} • Export inclusief afbeeldingen</div>'
CENTRAL_FOOTER = f'<div class="side-foot">Centrale synchronisatie • Netlify + Clerk<br><br>v{version} • Export inclusief afbeeldingen</div>'
LEGACY_FOOTER = '<div class="side-foot">Centrale synchronisatie • Netlify + Clerk<br><br>v1.64 • Export inclusief afbeeldingen</div>'

if MARKER not in text:
    source_footer = next((candidate for candidate in (LOCAL_FOOTER, CENTRAL_FOOTER, LEGACY_FOOTER) if candidate in text), None)
    if not source_footer:
        raise SystemExit('Buildvalidatie mislukt: versiefooter niet gevonden')

    local_synology = source_footer == LOCAL_FOOTER
    sync_label = 'Lokale synchronisatie • Synology' if local_synology else 'Centrale synchronisatie • Netlify + Clerk'
    storage_label = '<span>Eigen beheer • lokale opslag</span><br>' if local_synology else ''
    footer = f'''<div class="side-foot" {MARKER}>{sync_label}<br><br>{storage_label}<span id="machineparkVersion">v{version}</span><br><span id="machineparkBuildMeta" style="display:inline-block;margin-top:4px">Buildinformatie laden…</span><br><span>Export inclusief afbeeldingen</span></div>'''
    text = text.replace(source_footer, footer, 1)

    script = '''\n<script data-machinepark-build-info-script="visible-build-info-v1">\n(() => {\n  const versionEl = document.getElementById('machineparkVersion');\n  const metaEl = document.getElementById('machineparkBuildMeta');\n  if (!versionEl || !metaEl) return;\n\n  const fallbackVersion = versionEl.textContent.replace(/^v/i, '').trim();\n  const shortSha = value => String(value || '').trim().slice(0, 8);\n  const formatBuiltAt = value => {\n    if (!value) return '';\n    const date = new Date(value);\n    if (Number.isNaN(date.getTime())) return '';\n    try {\n      return new Intl.DateTimeFormat('nl-BE', {\n        day: '2-digit', month: '2-digit', year: 'numeric',\n        hour: '2-digit', minute: '2-digit',\n      }).format(date);\n    } catch (_) {\n      return date.toLocaleString();\n    }\n  };\n\n  fetch('./deploy-meta.json?machineparkBuildInfo=' + Date.now(), { cache: 'no-store' })\n    .then(response => response.ok ? response.json() : null)\n    .then(meta => {\n      if (!meta) {\n        metaEl.textContent = 'Build: webversie';\n        return;\n      }\n      const appVersion = String(meta.app_version || fallbackVersion).trim();\n      versionEl.textContent = 'v' + appVersion;\n      const builtAt = formatBuiltAt(meta.built_at);\n      const sha = shortSha(meta.source_sha);\n      const parts = [];\n      if (builtAt) parts.push('Build ' + builtAt);\n      if (sha) parts.push(sha);\n      metaEl.textContent = parts.length ? parts.join(' • ') : 'Buildinformatie beschikbaar';\n    })\n    .catch(() => {\n      metaEl.textContent = 'Build: webversie';\n    });\n})();\n</script>\n'''

    if '</body>' not in text:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt')
    text = text.replace('</body>', script + '</body>', 1)

index_path.write_text(text, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    f'id="machineparkVersion">v{version}<',
    'id="machineparkBuildMeta"',
    'deploy-meta.json?machineparkBuildInfo=',
    'meta.app_version',
    'meta.built_at',
    'meta.source_sha',
]
for token in required:
    if token not in built:
        raise SystemExit('Buildvalidatie mislukt: ontbreekt: ' + token)

print(f'Zichtbare buildinformatie toegevoegd voor v{version}.')
