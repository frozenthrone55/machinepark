from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
package_path = ROOT / 'package.json'

text = index_path.read_text(encoding='utf-8')
package = json.loads(package_path.read_text(encoding='utf-8'))
version = str(package.get('version') or '').strip()
if not version:
    raise SystemExit('Buildvalidatie mislukt: package.json bevat geen versie')

MARKER = 'data-machinepark-build-info="visible-build-info-v1"'
SCRIPT_MARKER = 'data-machinepark-build-info-script="visible-build-info-v1"'
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

version_pattern = re.compile(r'(<span id="machineparkVersion">)v[^<]*(</span>)')
text, version_updates = version_pattern.subn(lambda match: f'{match.group(1)}v{version}{match.group(2)}', text, count=1)
if version_updates != 1:
    raise SystemExit('Buildvalidatie mislukt: zichtbare versie kon niet worden ververst')

script = '''
<script data-machinepark-build-info-script="visible-build-info-v1">
(() => {
  const versionEl = document.getElementById('machineparkVersion');
  const metaEl = document.getElementById('machineparkBuildMeta');
  if (!versionEl || !metaEl) return;

  const fallbackVersion = versionEl.textContent.replace(/^v/i, '').trim();
  const shortSha = value => String(value || '').trim().slice(0, 8);
  const formatBuiltAt = value => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    try {
      return new Intl.DateTimeFormat('nl-BE', {
        timeZone: 'Europe/Brussels',
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      }).format(date);
    } catch (_) {
      return date.toLocaleString('nl-BE', { timeZone: 'Europe/Brussels' });
    }
  };

  fetch('./deploy-meta.json?machineparkBuildInfo=' + Date.now(), { cache: 'no-store' })
    .then(response => response.ok ? response.json() : null)
    .then(meta => {
      if (!meta) {
        metaEl.textContent = 'Build: webversie';
        return;
      }
      const appVersion = String(meta.app_version || fallbackVersion).trim();
      versionEl.textContent = 'v' + appVersion;
      const builtAt = formatBuiltAt(meta.built_at);
      const sha = shortSha(meta.source_sha);
      const parts = [];
      if (builtAt) parts.push('Build ' + builtAt);
      if (sha) parts.push(sha);
      metaEl.textContent = parts.length ? parts.join(' • ') : 'Buildinformatie beschikbaar';
    })
    .catch(() => {
      metaEl.textContent = 'Build: webversie';
    });
})();
</script>
'''

script_pattern = re.compile(r'\n?<script data-machinepark-build-info-script="visible-build-info-v1">.*?</script>\n?', re.S)
if SCRIPT_MARKER in text:
    text, script_updates = script_pattern.subn(script, text, count=1)
    if script_updates != 1:
        raise SystemExit('Buildvalidatie mislukt: bestaand buildinfoscript kon niet worden ververst')
else:
    body_end = text.rfind('</body>')
    if body_end < 0:
        raise SystemExit('Buildvalidatie mislukt: finale </body> ontbreekt')
    text = text[:body_end] + script + text[body_end:]

index_path.write_text(text, encoding='utf-8')

built = index_path.read_text(encoding='utf-8')
required = [
    MARKER,
    SCRIPT_MARKER,
    f'id="machineparkVersion">v{version}<',
    'id="machineparkBuildMeta"',
    'deploy-meta.json?machineparkBuildInfo=',
    "timeZone: 'Europe/Brussels'",
    "second: '2-digit'",
    'meta.app_version',
    'meta.built_at',
    'meta.source_sha',
]
for token in required:
    if token not in built:
        raise SystemExit('Buildvalidatie mislukt: ontbreekt: ' + token)

script_at = built.find(SCRIPT_MARKER)
final_body_at = built.rfind('</body>')
if script_at < 0 or final_body_at < 0 or script_at > final_body_at:
    raise SystemExit('Buildvalidatie mislukt: buildinfoscript staat niet vóór de finale body-tag')

print(f'Zichtbare buildinformatie toegevoegd/ververst voor v{version}.')
