(() => {
  const endpoint = './synology/api/sharepoint-device-sync.php';
  const fmt = v => v ? new Date(v).toLocaleString('nl-BE') : 'Nog niet uitgevoerd';
  let busy = false, nextOffset = null;
  async function load() {
    const card = document.getElementById('automaticDeviceSync');
    if (!card || !window.machineparkIsAdmin) return;
    try {
      const data = await adminFetch(endpoint);
      const sync = data.sync || {}, latest = sync.lastRun;
      card.querySelector('[data-sync-status]').textContent = data.ready ? (sync.enabled ? 'Automatische synchronisatie ingeschakeld' : 'Automatische synchronisatie uitgeschakeld') : 'Nog in te stellen: ' + data.setupMessage;
      card.querySelector('[data-sync-summary]').textContent = `Laatste controle: ${fmt(sync.lastCheckAt)}${sync.lastCheckStatus ? ' (' + ({unchanged:'bestand ongewijzigd',success:'geslaagd',error:'mislukt'})[sync.lastCheckStatus] + ')' : ''} · Laatste geslaagde synchronisatie: ${fmt(sync.lastSuccessAt)}${latest ? ' · ' + latest.message : ''}`;
      const enable = card.querySelector('[data-sync-enable]');
      enable.checked = !!sync.enabled;
      enable.disabled = !data.ready || busy;
      card.querySelector('[data-sync-run]').disabled = !data.ready || busy;
      card.querySelector('[data-sync-refresh]').disabled = busy;
      card.querySelector('[data-sync-history]').innerHTML = (data.history || []).map(run => `<details style="margin-top:12px"><summary><strong>${esc(fmt(run.at))}</strong> · ${esc(run.message)} · ${esc(run.status)}</summary><p class="muted">${esc(run.fileName || '')} · Bestandsversie: ${esc(run.version || '—')} · ${Number(run.read || 0)} toestellen gelezen · ${Number(run.added || 0)} nieuw · ${Number(run.updated || 0)} bijgewerkt</p>${run.skipped?.length ? `<p>${esc(run.skipped.join(' · '))}</p>` : ''}<div class="table-wrap"><table class="table"><thead><tr><th>Toestel</th><th>Veld</th><th>Oude waarde</th><th>Nieuwe waarde</th></tr></thead><tbody>${(run.changes || []).map(c => `<tr><td>${esc(c.code)}</td><td>${esc(({location:'Locatie',brand:'Merk / toestelgegevens',installDate:'Contract start',installDatePrecision:'Datumprecisie',installDateSource:'Bron contract start',status:'Status',assetCode:'WCL nr.'})[c.field] || c.field)}</td><td>${esc(c.oldValue || '—')}</td><td>${esc(c.newValue || '—')}</td></tr>`).join('') || '<tr><td colspan="4">Geen toestelwijzigingen.</td></tr>'}</tbody></table></div></details>`).join('') || '<p class="muted">Nog geen synchronisatiegeschiedenis.</p>';
      const more = card.querySelector('[data-sync-more]');
      nextOffset = data.nextOffset;
      more.hidden = nextOffset === null;
      more.onclick = async () => {
        more.disabled = true;
        try {
          const extra = await adminFetch(endpoint + '?offset=' + nextOffset);
          for (const run of extra.history || []) {
            const detail = document.createElement('details');
            const summary = document.createElement('summary');
            summary.textContent = fmt(run.at) + ' · ' + run.message + ' · ' + run.status;
            detail.append(summary);
            const table = document.createElement('table'); table.className = 'table';
            table.innerHTML = '<thead><tr><th>Toestel</th><th>Veld</th><th>Oude waarde</th><th>Nieuwe waarde</th></tr></thead><tbody>' + (run.changes || []).map(c => `<tr><td>${esc(c.code)}</td><td>${esc(c.field)}</td><td>${esc(c.oldValue || '—')}</td><td>${esc(c.newValue || '—')}</td></tr>`).join('') + '</tbody>';
            const wrap = document.createElement('div'); wrap.className = 'table-wrap'; wrap.append(table); detail.append(wrap);
            card.querySelector('[data-sync-history]').append(detail);
          }
          nextOffset = extra.nextOffset; more.hidden = nextOffset === null;
        } catch(e) { toast(e.message); } finally { more.disabled = false; }
      };
    } catch (e) { card.querySelector('[data-sync-status]').textContent = e.message; }
  }
  async function action(body) {
    if (busy) return;
    busy = true;
    document.querySelectorAll('#automaticDeviceSync button, #automaticDeviceSync input').forEach(el => el.disabled = true);
    try { await adminFetch(endpoint, {method:'POST', body:JSON.stringify(body)}); if (body.action === 'run') { await centralPull({quiet:true}); await refresh(); } }
    catch (e) { toast(e.message); }
    finally { busy = false; await load(); }
  }
  function init() {
    if (!document.querySelector('meta[name="machinepark-auth"][content="synology-local"]')) return;
    const anchor = document.getElementById('syncDevicesExcelBtn')?.closest('.settings-card');
    if (!anchor || document.getElementById('automaticDeviceSync')) return;
    anchor.insertAdjacentHTML('afterend', `<div class="settings-card" id="automaticDeviceSync"><h4>Automatische toestelsynchronisatie</h4><p>Controleert de Excelbron via de geplande NAS-taak. Bij een lokale OneDrive-kopie moet je pc aanstaan en met OneDrive en de NAS verbonden zijn om nieuwe wijzigingen aan te leveren. Alleen bij een gewijzigde versie worden toestellen verwerkt met dezelfde regels als de handmatige synchronisatie.</p><p data-sync-status>Gegevens laden…</p><p class="muted" data-sync-summary></p><label style="display:flex;gap:8px;align-items:center"><input type="checkbox" data-sync-enable> Automatisch controleren (elke 5 minuten)</label><div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap"><button class="btn primary" data-sync-run>Nu controleren</button><button class="btn" data-sync-refresh>Vernieuwen</button></div><p class="muted">Het Excelbestand wordt uitsluitend gelezen. Toestellen die ontbreken in Excel worden niet verwijderd. De historiek toont de wijzigingen vanaf ingebruikname.</p><div data-sync-history></div><button class="btn" data-sync-more hidden>Oudere synchronisaties</button></div>`);
    const card = document.getElementById('automaticDeviceSync');
    card.querySelector('[data-sync-enable]').onchange = e => action({action:'enable',enabled:e.target.checked});
    card.querySelector('[data-sync-run]').onclick = () => action({action:'run'});
    card.querySelector('[data-sync-refresh]').onclick = load;
    const original = loadAdminPanels;
    loadAdminPanels = async function(...args) { await Promise.all([original.apply(this,args),load()]); };
    if (window.machineparkIsAdmin) load();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded',init); else init();
})();
