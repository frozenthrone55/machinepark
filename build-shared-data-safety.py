from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="shared-data-safety-v1"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="shared-data-safety-v1">
(() => {
  const host = String(location.hostname || '').toLowerCase();
  const nonProductionHost =
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host.startsWith('deploy-preview-') ||
    host.startsWith('development--');

  window.machineparkServiceBlobWritesEnabled = !nonProductionHost;

  if (nonProductionHost && typeof window.machineparkPersistServicePhotos === 'function') {
    // Development en production delen de centrale snapshot. Een preview mag daarom
    // bestaande verslagfoto’s niet automatisch naar refs omzetten die de oude main
    // nog niet kan weergeven. Na een expliciete merge activeert dit vanzelf op productie.
    window.machineparkPersistServicePhotos = async function(_storeName, _entityId, photos) {
      return (Array.isArray(photos) ? photos : [])
        .filter((src) => typeof src === 'string' && src.trim())
        .slice(0, 5);
    };
  }
})();
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor gedeelde-data beveiliging')
    before, after = index.rsplit('</body>', 1)
    index = before + script + '</body>' + after
    index_path.write_text(index, encoding='utf-8')

for needle in [MARKER, 'machineparkServiceBlobWritesEnabled', "host.startsWith('deploy-preview-')", 'machineparkPersistServicePhotos']:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: gedeelde-data beveiliging ontbreekt ({needle})')

print('[Machinepark] preview beschermt productiecompatibiliteit van gedeelde verslagfoto-data')
