(() => {
  const definitions = [
    ['documents','Overzichten & documenten','Samengestelde overzichten, werkbonnen en handleidingen'],
    ['imports','Import & synchronisatie','Excel, toestellen en foto-import'],
    ['users','Gebruikers & rechten','Accounts, rollen en toegangsrechten'],
    ['settings','Instellingen & koppelingen','Algemene instellingen en Outlook Classic'],
    ['technical','Technisch beheer','Back-up, logboek, herstel en onderhoud']
  ];
  const key = text => String(text || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
  function category(card) {
    const title=key(card.querySelector('h4,h3')?.textContent);
    if (/gebruikers|rollen|rechten/.test(title)) return 'users';
    if (/import|excel|synchron|toestelmap/.test(title)) return 'imports';
    if (/samengesteld|handleiding|werkbon/.test(title)) return 'documents';
    if (/back.up|logboek|herstel|migratie|wissen|opschonen/.test(title)) return 'technical';
    return 'settings';
  }
  function init() {
    const root=document.querySelector('#view-settings > .settings-grid');
    if (!root || root.dataset.adminGroups) return;
    root.dataset.adminGroups='1';root.classList.add('admin-group-list');
    const groups=new Map();
    for (const [id,title,description] of definitions) {
      const group=document.createElement('details');group.className='admin-group';group.dataset.adminGroup=id;
      const summary=document.createElement('summary');
      const name=document.createElement('strong');name.textContent=title;
      const hint=document.createElement('small');hint.textContent=description;
      summary.append(name,hint);
      const body=document.createElement('div');body.className='admin-group-body';
      group.append(summary,body);root.append(group);groups.set(id,{group,body});
    }
    function organize() {
      for(const card of root.querySelectorAll('.settings-card')) {
        if(card.dataset.adminGrouped)continue;
        card.dataset.adminGrouped='1';groups.get(category(card)).body.append(card);
        const history=card.querySelector('[data-sync-history]');
        if(history && !history.closest('.admin-sync-history')) {
          const details=document.createElement('details');details.className='admin-sync-history';
          const summary=document.createElement('summary');summary.textContent='Historiek van wijzigingen';
          history.before(details);details.append(summary,history);
          const more=card.querySelector('[data-sync-more]');if(more)details.append(more);
        }
      }

    }
    organize();

    let queued=false;
    new MutationObserver(records=>{
      if(!records.some(record=>[...record.addedNodes].some(node=>node.nodeType===1 && (node.matches?.('.settings-card') || node.querySelector?.('.settings-card')))))return;
      if(queued)return;queued=true;queueMicrotask(()=>{queued=false;organize();});
    }).observe(root,{childList:true,subtree:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
