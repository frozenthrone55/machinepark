from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="role-settings-actions-v1"'

if MARKER not in index:
    script = r'''
<script data-machinepark-build-fix="role-settings-actions-v1">
(() => {
  const previousApplyOperationalPermissions = applyOperationalPermissions;
  applyOperationalPermissions = function() {
    previousApplyOperationalPermissions();
    const rules = [
      ['#exportBackup', 'backup.export'],
      ['#importBackup', 'backup.import'],
      ['#importStockExcelBtn', 'parts.import'],
      ['#syncDevicesExcelBtn', 'devices.import'],
    ];
    rules.forEach(([selector, permission]) => {
      document.querySelectorAll(selector).forEach((el) => {
        el.style.display = window.machineparkHasPermission?.(permission) ? '' : 'none';
      });
    });
  };
  window.applyOperationalPermissions = applyOperationalPermissions;
  if (window.machineparkAccessReady) applyOperationalPermissions();
})();
</script>
'''
    if '</body>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </body> ontbreekt voor beheerrechten')
    index = index.replace('</body>', script + '</body>', 1)
    index_path.write_text(index, encoding='utf-8')

for needle in [MARKER, 'backup.export', 'backup.import', 'parts.import', 'devices.import']:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: beheeractie-recht ontbreekt ({needle})')

print('[Machinepark] back-up- en Excelbeheer gekoppeld aan rollenrechten')
