from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
index = INDEX.read_text(encoding="utf-8")
MARKER = 'data-machinepark-build-fix="synology-cloud-export-v1"'

if MARKER not in index:
    anchor = '<div class="settings-card"><h4>Back-up</h4>'
    if anchor not in index:
        raise SystemExit("Buildvalidatie mislukt: Back-upkaart niet gevonden voor Synology cloudexport")

    card = '''<div class="settings-card">
          <h4>Synology cloudexport</h4>
          <p>Maak een eenmalig exportpakket van de resterende online Machinepark-gegevens voor de lokale Synology: rollen, Storingen, werkbonnen, handleidingen + PDF-bestanden, gebruikerslijst en historisch logboek.</p>
          <button class="btn primary" type="button" id="exportSynologyCloudBtn">Export voor Synology maken</button>
          <div id="exportSynologyCloudStatus" class="muted" style="font-size:11px;margin-top:9px;line-height:1.45"></div>
        </div>
        '''
    index = index.replace(anchor, card + anchor, 1)

    feature = r'''
<script data-machinepark-build-fix="synology-cloud-export-v1">
(() => {
  const ENDPOINTS = {
    roles: '/.netlify/functions/role-management',
    faults: '/.netlify/functions/fault-library',
    workOrders: '/.netlify/functions/work-order-templates',
    manuals: '/.netlify/functions/manual-library',
    users: '/.netlify/functions/user-management',
    audit: '/.netlify/functions/audit-log',
  };

  function cloudExportStatus(message, kind = '') {
    const el = document.getElementById('exportSynologyCloudStatus');
    if (!el) return;
    el.textContent = message || '';
    el.style.color = kind === 'error' ? '#a13b3b' : (kind === 'ok' ? '#247458' : '');
  }

  async function cloudGetJson(url) {
    const response = await fetch(url, {
      method: 'GET',
      headers: await centralHeaders(false),
      cache: 'no-store',
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || ('Cloudexport mislukt (' + response.status + ')'));
    return body;
  }

  async function cloudGetPdf(fileKey) {
    const url = ENDPOINTS.manuals + '?file=' + encodeURIComponent(String(fileKey || ''));
    const response = await fetch(url, {
      method: 'GET',
      headers: await centralHeaders(false),
      cache: 'no-store',
    });
    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(text || ('PDF kon niet worden gelezen (' + response.status + ')'));
    }
    const buffer = await response.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    if (!bytes.length) throw new Error('Een handleiding-PDF is leeg.');
    let binary = '';
    const chunk = 0x8000;
    for (let i = 0; i < bytes.length; i += chunk) {
      binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
    }
    return {
      base64: btoa(binary),
      size: bytes.length,
      contentType: response.headers.get('content-type') || 'application/pdf',
    };
  }

  function cleanAuditEntries(entries) {
    return (Array.isArray(entries) ? entries : []).map((entry) => ({
      ...entry,
      changes: (Array.isArray(entry?.changes) ? entry.changes : []).map((change) => {
        const { undo, reversible, linkedUndoCount, ...safe } = change || {};
        return { ...safe, reversible: false };
      }),
    }));
  }

  async function buildSynologyCloudExport() {
    cloudExportStatus('Cloudgegevens ophalen…');
    const [roles, faults, workOrders, manuals, users, audit] = await Promise.all([
      cloudGetJson(ENDPOINTS.roles),
      cloudGetJson(ENDPOINTS.faults),
      cloudGetJson(ENDPOINTS.workOrders),
      cloudGetJson(ENDPOINTS.manuals),
      cloudGetJson(ENDPOINTS.users),
      cloudGetJson(ENDPOINTS.audit),
    ]);

    const manualItems = Array.isArray(manuals.manuals) ? manuals.manuals : [];
    const files = {};
    for (let i = 0; i < manualItems.length; i++) {
      const manual = manualItems[i];
      if (!manual?.fileKey) continue;
      cloudExportStatus('Handleidingen ophalen · ' + (i + 1) + ' van ' + manualItems.length + ' · ' + (manual.title || manual.fileName || 'PDF'));
      const pdf = await cloudGetPdf(manual.fileKey);
      files[manual.fileKey] = {
        fileName: manual.fileName || 'handleiding.pdf',
        fileSize: pdf.size,
        contentType: pdf.contentType,
        base64: pdf.base64,
      };
    }

    const packageData = {
      app: 'Machinepark',
      schema: 1,
      exportKind: 'synology-cloud-config-v1',
      exportedAt: new Date().toISOString(),
      source: {
        origin: location.origin,
        hostname: location.hostname,
        preview: location.hostname.includes('deploy-preview-') || location.hostname.includes('development--'),
      },
      roles: {
        roles: Array.isArray(roles.roles) ? roles.roles : [],
        permissionCatalog: Array.isArray(roles.permissionCatalog) ? roles.permissionCatalog : [],
      },
      faults: {
        faults: Array.isArray(faults.faults) ? faults.faults : [],
      },
      workOrders: {
        templates: Array.isArray(workOrders.templates) ? workOrders.templates : [],
      },
      manuals: {
        items: manualItems,
        files,
      },
      users: {
        users: Array.isArray(users.users) ? users.users : [],
        invitations: Array.isArray(users.invitations) ? users.invitations : [],
      },
      audit: {
        entries: cleanAuditEntries(audit.entries),
      },
      counts: {
        roles: Array.isArray(roles.roles) ? roles.roles.length : 0,
        faults: Array.isArray(faults.faults) ? faults.faults.length : 0,
        workOrders: Array.isArray(workOrders.templates) ? workOrders.templates.length : 0,
        manuals: manualItems.length,
        users: Array.isArray(users.users) ? users.users.length : 0,
        auditEntries: Array.isArray(audit.entries) ? audit.entries.length : 0,
      },
    };

    return packageData;
  }

  function downloadSynologyCloudExport(data) {
    const date = new Date().toISOString().slice(0, 10);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Machinepark_Synology_CloudExport_' + date + '.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function runSynologyCloudExport() {
    const button = document.getElementById('exportSynologyCloudBtn');
    if (!button) return;
    button.disabled = true;
    try {
      const data = await buildSynologyCloudExport();
      downloadSynologyCloudExport(data);
      const c = data.counts || {};
      cloudExportStatus(
        'Export klaar · ' +
        (c.roles || 0) + ' rollen · ' +
        (c.faults || 0) + ' storingen · ' +
        (c.workOrders || 0) + ' werkbonnen · ' +
        (c.manuals || 0) + ' handleidingen · ' +
        (c.users || 0) + ' gebruikers · ' +
        (c.auditEntries || 0) + ' logboekregels',
        'ok'
      );
    } catch (error) {
      console.error('Synology cloudexport', error);
      cloudExportStatus(error?.message || 'Cloudexport mislukt.', 'error');
      alert('Synology cloudexport mislukt: ' + (error?.message || 'onbekende fout'));
    } finally {
      button.disabled = false;
    }
  }

  function bindSynologyCloudExport() {
    const button = document.getElementById('exportSynologyCloudBtn');
    if (button && !button.dataset.bound) {
      button.dataset.bound = '1';
      button.addEventListener('click', runSynologyCloudExport);
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindSynologyCloudExport, { once: true });
  } else {
    bindSynologyCloudExport();
  }
})();
</script>
'''
    body_pos = index.rfind('</body>')
    if body_pos < 0:
        raise SystemExit("Buildvalidatie mislukt: </body> ontbreekt voor Synology cloudexport")
    index = index[:body_pos] + feature + '\n' + index[body_pos:]
    INDEX.write_text(index, encoding="utf-8")

built = INDEX.read_text(encoding="utf-8")
for needle in [
    MARKER,
    'id="exportSynologyCloudBtn"',
    "synology-cloud-config-v1",
    "/.netlify/functions/manual-library",
    "Machinepark_Synology_CloudExport_",
    "cleanAuditEntries",
]:
    if needle not in built:
        raise SystemExit(f"Buildvalidatie mislukt: Synology cloudexport ontbreekt ({needle})")

print("[Machinepark] eenmalige Synology cloudexport toegevoegd aan Beheer")
