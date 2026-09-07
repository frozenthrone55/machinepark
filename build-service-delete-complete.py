from pathlib import Path

ROOT = Path(__file__).resolve().parent
index_path = ROOT / 'index.html'
index = index_path.read_text(encoding='utf-8')
MARKER = 'data-machinepark-build-fix="service-delete-complete-v1"'

if MARKER not in index:
    start = index.find('async function deleteServiceRecord(storeName,id){')
    end = index.find('function deviceSearchField', start)
    if start < 0 or end < 0:
        raise SystemExit('Buildvalidatie mislukt: verwijderfunctie voor onderhoud/depannage niet gevonden')

    replacement = r'''function serviceDeleteImpact(record){
  const used=(Array.isArray(record?.usedParts)?record.usedParts:[]).filter(u=>u?.partId&&Number(u?.qty||0)>0);
  const usedQty=used.reduce((sum,u)=>sum+Number(u.qty||0),0);
  const oneOff=(Array.isArray(record?.oneOffParts)?record.oneOffParts:[]).filter(item=>item&&(item.supplierCode||item.description));
  const photos=(Array.isArray(record?.photos)?record.photos:[]).filter(src=>typeof src==='string'&&src.trim());
  const sessions=(Array.isArray(record?.workSessions)?record.workSessions:[]).filter(Boolean);
  const hasWorkOrder=Boolean(record?.workOrder&&Array.isArray(record.workOrder.fields));
  return {usedTypes:new Set(used.map(u=>String(u.partId))).size,usedQty,oneOff:oneOff.length,photos:photos.length,sessions:sessions.length,hasWorkOrder};
}
async function deleteServiceRecord(storeName,id){
  const collection=storeName==='maintenance'?state.maintenance:storeName==='breakdowns'?state.breakdowns:null;
  if(!collection)return;
  const record=collection.find(item=>item.id===id);
  if(!record){toast('Registratie niet meer gevonden');return}
  const kind=storeName==='maintenance'?'onderhoud':'depannage',device=deviceName(record.deviceId,recordMoment(record)),impact=serviceDeleteImpact(record);
  const lines=[`${kind==='onderhoud'?'Onderhoud':'Depannage'} van ${device} definitief verwijderen?`,''];
  if(impact.usedQty>0){
    lines.push('Alle gebruikte onderdelen van deze registratie worden automatisch terug op voorraad gezet.');
    lines.push(`• In totaal ${impact.usedQty} stuk${impact.usedQty===1?'':'s'} uit ${impact.usedTypes} voorraadtype${impact.usedTypes===1?'':'s'}.`);
  }else lines.push('• Er zijn geen gebruikte voorraadonderdelen om terug op voorraad te zetten.');
  if(impact.oneOff)lines.push(`• ${impact.oneOff} eenmalig onderdeel${impact.oneOff===1?'':'delen'} wordt/worden samen met de registratie verwijderd.`);
  if(impact.sessions||impact.hasWorkOrder)lines.push('• Werkdagen, werkuren en gekoppelde werkbongegevens worden samen met de registratie verwijderd.');
  if(impact.photos)lines.push(`• ${impact.photos} verslagfoto${impact.photos===1?'':'\'s'} wordt/worden na centrale synchronisatie uit de gekoppelde foto-opslag verwijderd.`);
  lines.push('','De verwijdering, voorraadcorrectie en alle gekoppelde gegevens worden samen gesynchroniseerd en in het wijzigingslogboek opgenomen.');
  if(!confirm(lines.join('\n')))return;
  try{
    const result=await deleteServiceRecordAtomic(storeName,record);
    closeModal();
    await refresh();
    const restored=result.restoredQuantity?` · ${result.restoredQuantity} stuk${result.restoredQuantity===1?'':'s'} terug op voorraad`:'';
    toast(`${kind==='onderhoud'?'Onderhoud':'Depannage'} volledig verwijderd${restored}`);
  }catch(error){
    console.error('Registratie verwijderen',error);
    alert(error?.message||'Verwijderen mislukt.');
  }
}
'''
    index = index[:start] + replacement + index[end:]
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: </head> ontbreekt voor service-delete marker')
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    index_path.write_text(index, encoding='utf-8')

required = [
    MARKER,
    'function serviceDeleteImpact(record)',
    "storeName==='maintenance'?state.maintenance:storeName==='breakdowns'?state.breakdowns:null",
    'record?.oneOffParts',
    'record?.workSessions',
    'record?.workOrder',
    'record?.photos',
    'Alle gebruikte onderdelen van deze registratie worden automatisch terug op voorraad gezet.',
    'alle gekoppelde gegevens worden samen gesynchroniseerd',
    "deleteServiceRecordAtomic(storeName,record)",
]
for needle in required:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: volledige serviceverwijdering ontbreekt ({needle})')

# Voorraadherstel en verwijderen moeten in één lokale IndexedDB-transactie blijven.
for needle in [
    "if(!['maintenance','breakdowns'].includes(storeName))",
    "db.transaction([storeName,'parts'],'readwrite')",
    "stock:Number(part.stock||0)+qty",
    'records.delete(record.id)',
    'scheduleCentralSync()',
]:
    if needle not in index:
        raise SystemExit(f'Buildvalidatie mislukt: atomaire serviceverwijdering ontbreekt ({needle})')

print('[Machinepark] onderhoud en depannages worden volledig verwijderd inclusief gekoppelde effecten')
