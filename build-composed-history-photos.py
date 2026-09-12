from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-documents-v1"'
MARKER = 'data-machinepark-build-fix="composed-history-photos-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: samengestelde documenten ontbreken voor geschiedenis/foto-fix')

if MARKER not in index:
    style = r'''
<style data-machinepark-build-fix="composed-history-photos-v1">
.composed-history-intro{margin:22px 0 10px}.composed-history-intro h2{margin:0 0 4px;font-size:19px}.composed-history-intro p{margin:0;color:var(--muted);font-size:12px}
.composed-location-history{border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:13px 0 20px;background:#fff;break-inside:auto}
.composed-location-history-head{padding:12px 14px;background:#eef4f1;border-bottom:1px solid var(--line);display:flex;justify-content:space-between;gap:10px;align-items:center;flex-wrap:wrap}.composed-location-history-head h3{margin:0;font-size:15px;text-transform:none;letter-spacing:0;color:var(--brand)}.composed-location-history-head span{font-size:11px;color:var(--muted);font-weight:700}
.composed-history-list{display:grid;gap:0}.composed-history-event{padding:13px 14px;border-bottom:1px solid #e7ece9;break-inside:avoid}.composed-history-event:last-child{border-bottom:0}.composed-history-event-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;flex-wrap:wrap}.composed-history-event-title{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.composed-history-event-title strong{font-size:13px}.composed-history-date{font-size:11px;color:var(--muted);white-space:nowrap}.composed-history-meta{font-size:11px;color:#53615b;margin-top:5px;display:flex;gap:8px 14px;flex-wrap:wrap}
.composed-history-work{margin-top:9px;padding:9px 10px;border:1px solid #e3e9e6;border-radius:10px;background:#f9fbfa}.composed-history-work-head{font-size:11px;font-weight:800;margin-bottom:4px}.composed-history-work-detail{font-size:11px;line-height:1.45;white-space:pre-wrap}.composed-history-work-parts{margin-top:5px;font-size:10.5px;color:#4f5d57}
.composed-history-photos{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:9px;margin-top:11px}.composed-history-photo{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;border:1px solid var(--line);border-radius:10px;background:#eef2f0;cursor:zoom-in;break-inside:avoid}.composed-history-photo:hover{box-shadow:0 5px 16px rgba(20,45,38,.15)}
.composed-overview-devices{margin:14px 0 20px}
@media(max-width:700px){.composed-history-photos{grid-template-columns:repeat(2,minmax(0,1fr))}.composed-history-event{padding:11px}.composed-location-history-head{padding:11px 12px}}
@media print{.composed-location-history{break-inside:auto}.composed-history-event{break-inside:avoid}.composed-history-photos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm}.composed-history-photo{width:100%!important;height:45mm!important;aspect-ratio:auto;object-fit:contain!important;background:#fff;border:1px solid #bbb;border-radius:2mm}}
</style>
'''
    if '</head>' not in index:
        raise SystemExit('Buildvalidatie mislukt: HTML-head ontbreekt voor geschiedenis/foto-fix')
    index = index.replace('</head>', style + '</head>', 1)

    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker, gevonden {index.count(anchor)}x')

    script = r'''
  function composedHistoryIsVideo(src){
    const value=String(src||'').trim();
    if(!value)return false;
    if(typeof window.machineparkIsVideoMedia==='function')return Boolean(window.machineparkIsVideoMedia(value));
    return value.startsWith('data:video/')||/[?&]media=video(?:&|$)/.test(value);
  }
  function composedHistoryPhotoList(rows){
    const seen=new Set(),photos=[];
    (rows||[]).forEach(row=>(row?.item?.photos||[]).forEach(src=>{
      const value=typeof src==='string'?src.trim():'';
      if(!value||composedHistoryIsVideo(value)||seen.has(value))return;
      seen.add(value);photos.push(value);
    }));
    return photos;
  }
  function composedHistoryDeviceLabel(device){return [device?.assetCode,device?.brand,device?.model].filter(Boolean).join(' · ')||'Onbekend toestel';}
  function composedHistoryMoment(record){
    const date=record?.serviceReportDate||record?.serviceVisitDate||record?.date||'';
    const time=record?.serviceReportTime||record?.serviceVisitTime||record?.time||'';
    if(/^\d{4}-\d{2}-\d{2}$/.test(String(date)))return `${date}T${/^\d{2}:\d{2}/.test(String(time))?time:'00:00:00'}`;
    return String(record?.serviceReportClosedAt||record?.serviceVisitClosedAt||record?.updatedAt||record?.createdAt||date||'');
  }
  function composedHistoryLocation(device,record,moment=''){
    return String(record?.serviceVisitLocation||record?.location||composedLocation(device,moment)||device?.location||'Locatie onbekend').trim()||'Locatie onbekend';
  }
  function composedHistoryRows(snapshot){
    const devices=new Map((snapshot?.devices||[]).map(device=>[device.id,device]));
    const events=[],reports=new Map();
    for(const device of devices.values()){
      const rows=deviceRecords(snapshot,device.id);
      for(const row of rows){
        const record=row.item||{},moment=composedHistoryMoment(record),location=composedHistoryLocation(device,record,moment);
        const link=record.serviceVisitId||record.serviceReportId||'';
        if(link){
          const key=record.serviceVisitId?`visit:${record.serviceVisitId}`:`report:${record.serviceReportId}:${composedKey(location)}`;
          if(!reports.has(key))reports.set(key,{kind:'Serviceverslag',moment,location,rows:[],devices:new Set(),technicians:new Set()});
          const event=reports.get(key);event.rows.push(row);event.devices.add(composedHistoryDeviceLabel(device));
          const tech=String(record.serviceReportTechnician||record.serviceVisitTechnician||record.technician||'').trim();if(tech)event.technicians.add(tech);
          if(String(moment)>String(event.moment||''))event.moment=moment;
        }else{
          const tech=String(record.technician||'').trim();
          events.push({kind:row.kind,moment,location,rows:[row],devices:new Set([composedHistoryDeviceLabel(device)]),technicians:new Set(tech?[tech]:[])});
        }
      }
      (Array.isArray(device.locationHistory)?device.locationHistory:[]).forEach(entry=>{
        const location=String(entry?.location||'Locatie onbekend').trim()||'Locatie onbekend',moment=String(entry?.effectiveFrom||'');
        events.push({kind:'Locatiewijziging',moment,location,rows:[],devices:new Set([composedHistoryDeviceLabel(device)]),technicians:new Set(),details:`${composedHistoryDeviceLabel(device)} geregistreerd op deze locatie.`});
      });
    }
    reports.forEach(event=>events.push(event));
    events.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')));
    const grouped=new Map();
    events.forEach(event=>{
      const key=composedKey(event.location)||'locatie-onbekend';
      if(!grouped.has(key))grouped.set(key,{location:event.location,events:[]});
      grouped.get(key).events.push(event);
    });
    return [...grouped.values()].map(group=>({...group,events:[...group.events].sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')))})).sort((a,b)=>String(b.events[0]?.moment||'').localeCompare(String(a.events[0]?.moment||'')));
  }
  function composedHistoryPartsText(snapshot,record){
    const rows=recordParts(snapshot,record);return rows.length?rows.map(part=>`${part.code} × ${part.qty}${part.description?` · ${part.description}`:''}`).join(' | '):'';
  }
  function composedHistoryWorkHtml(snapshot,row){
    const record=row.item||{},device=(snapshot.devices||[]).find(item=>item.id===record.deviceId),parts=composedHistoryPartsText(snapshot,record),tech=record.technician||record.serviceVisitTechnician||record.serviceReportTechnician||'—';
    return `<div class="composed-history-work"><div class="composed-history-work-head">${composedEsc(row.kind)} · ${composedEsc(composedHistoryDeviceLabel(device))}</div><div class="composed-history-work-detail">${composedEsc(recordDescription(row.kind,record))}</div><div class="composed-history-meta"><span><strong>Technieker:</strong> ${composedEsc(tech)}</span></div>${parts?`<div class="composed-history-work-parts"><strong>Onderdelen:</strong> ${composedEsc(parts)}</div>`:''}</div>`;
  }
  function composedHistoryPhotosHtml(rows,label){
    const photos=composedHistoryPhotoList(rows);if(!photos.length)return '';
    return `<div class="composed-history-photos">${photos.map((src,index)=>`<img class="composed-history-photo" src="${composedEsc(src)}" data-full-src="${composedEsc(src)}" data-photo-lightbox loading="lazy" decoding="async" alt="${composedEsc(label)} foto ${index+1}" title="Klik om te vergroten">`).join('')}</div>`;
  }
  function composedHistoryEventHtml(snapshot,event){
    const rows=event.rows||[],photos=composedHistoryPhotosHtml(rows,event.kind),technicians=[...(event.technicians||[])],devices=[...(event.devices||[])];
    const details=rows.length?rows.map(row=>composedHistoryWorkHtml(snapshot,row)).join(''):`<div class="composed-history-work-detail">${composedEsc(event.details||'Locatie geregistreerd.')}</div>`;
    return `<article class="composed-history-event"><div class="composed-history-event-head"><div><div class="composed-history-event-title"><span class="badge">${composedEsc(event.kind)}</span><strong>${composedEsc(devices.join(', ')||'—')}</strong></div><div class="composed-history-meta">${technicians.length?`<span><strong>Technieker:</strong> ${composedEsc(technicians.join(', '))}</span>`:''}</div></div><div class="composed-history-date">${composedEsc(composedDate(event.moment))}</div></div>${details}${photos}</article>`;
  }
  function composedHistoryOverviewDevices(snapshot){
    const rows=(snapshot.devices||[]).map(device=>`<tr><td><strong>${composedEsc(device.assetCode||'—')}</strong></td><td>${composedEsc(composedLocation(device)||device.location||'—')}</td><td>${composedEsc([device.brand,device.model].filter(Boolean).join(' · ')||'—')}</td><td>${composedEsc(device.serial||'—')}</td><td>${composedEsc(device.status||'Actief')}</td></tr>`).join('');
    return rows?`<div class="composed-overview-devices"><table class="composed-doc-table"><thead><tr><th>WCL nr.</th><th>Huidige locatie</th><th>Toestel</th><th>Serienummer</th><th>Status</th></tr></thead><tbody>${rows}</tbody></table></div>`:'<div class="muted">Geen toestellen in dit overzicht.</div>';
  }
  function composedHistoryHtml(snapshot){
    const groups=composedHistoryRows(snapshot);if(!groups.length)return '<div class="composed-empty">Geen gebeurtenissen geregistreerd.</div>';
    return groups.map(group=>`<section class="composed-location-history"><div class="composed-location-history-head"><h3>${composedEsc(group.location)}</h3><span>${group.events.length} gebeurtenis${group.events.length===1?'':'sen'} · nieuwste eerst</span></div><div class="composed-history-list">${group.events.map(event=>composedHistoryEventHtml(snapshot,event)).join('')}</div></section>`).join('');
  }

  documentHtml=function(doc){
    const s=doc.snapshot||{devices:[],maintenance:[],breakdowns:[],parts:[]},groups=composedHistoryRows(s),allParts=mergedAllParts(s),totalEvents=groups.reduce((sum,group)=>sum+group.events.length,0),photoCount=groups.flatMap(group=>group.events).reduce((sum,event)=>sum+composedHistoryPhotoList(event.rows).length,0);
    const partsHtml=allParts.length?`<table class="composed-doc-table"><thead><tr><th>Onderdeel</th><th>Omschrijving</th><th>Totaal aantal</th><th>Toestellen</th></tr></thead><tbody>${allParts.map(part=>`<tr><td>${composedEsc(part.code)}</td><td>${composedEsc(part.description)}</td><td class="qty">${composedEsc(part.qty)}</td><td>${composedEsc(part.devices.join(', '))}</td></tr>`).join('')}</tbody></table>`:'<div class="muted">Geen onderdelen geregistreerd.</div>';
    return `<h1>${composedEsc(doc.name||'Samengesteld document')}</h1><div class="muted">Vastgelegd op ${composedEsc(composedDate(s.capturedAt||doc.createdAt))} · opgeslagen door ${composedEsc(doc.createdBy||'—')}</div><div class="composed-doc-summary"><div><span>Toestellen</span><strong>${(s.devices||[]).length}</strong></div><div><span>Gebeurtenissen</span><strong>${totalEvents}</strong></div><div><span>Verslagfoto’s</span><strong>${photoCount}</strong></div></div><div class="composed-subsection"><h3>Toestellen in dit overzicht</h3>${composedHistoryOverviewDevices(s)}</div><div class="composed-history-intro"><h2>Chronologische geschiedenis per locatie</h2><p>Onderhoud, depannages, serviceverslagen en andere relevante registraties · nieuwste gebeurtenis eerst. Foto’s staan bij het bijbehorende verslag.</p></div>${composedHistoryHtml(s)}<section class="composed-device-block"><h2>Totaal gebruikte onderdelen · alle geselecteerde toestellen</h2><div class="composed-subsection">${partsHtml}</div></section>`;
  };

  printStyles=function(){return `body{font-family:Arial,sans-serif;color:#17231f;margin:13mm;font-size:10px}h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:16px 0 6px}h3{font-size:12px}.muted{color:#67756f}.composed-doc-summary{display:flex;gap:7px;margin:12px 0}.composed-doc-summary>div{border:1px solid #dfe6e3;padding:7px;min-width:100px}.composed-doc-summary span{display:block;font-size:8px;text-transform:uppercase}.composed-doc-summary strong{display:block;margin-top:3px}.composed-doc-table{width:100%;border-collapse:collapse}.composed-doc-table th,.composed-doc-table td{border:1px solid #cfd8d4;padding:4px 5px;text-align:left;vertical-align:top;font-size:8.5px}.composed-location-history{border:1px solid #cfd8d4;margin:8px 0 12px;break-inside:auto}.composed-location-history-head{background:#eef4f1;padding:7px;border-bottom:1px solid #cfd8d4}.composed-location-history-head h3{margin:0}.composed-history-event{padding:7px;border-bottom:1px solid #dfe6e3;break-inside:avoid}.composed-history-event:last-child{border-bottom:0}.composed-history-event-head{display:flex;justify-content:space-between;gap:8px}.composed-history-event-title{display:flex;gap:5px;align-items:center}.badge{border:1px solid #cfd8d4;border-radius:99px;padding:2px 5px}.composed-history-meta,.composed-history-date{font-size:8px;color:#58655f}.composed-history-work{border:1px solid #e1e7e4;padding:5px;margin-top:5px;break-inside:avoid}.composed-history-work-head{font-weight:bold}.composed-history-photos{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:3mm;margin-top:3mm}.composed-history-photo{display:block;width:100%;height:45mm;object-fit:contain;border:1px solid #bbb;break-inside:avoid}.composed-device-block{break-inside:auto}.qty{text-align:right!important}@page{size:A4;margin:11mm}`;};
  printComposedDocument=function(doc){
    const win=window.open('','_blank');if(!win){alert('Het afdrukvenster kon niet worden geopend. Sta pop-ups toe en probeer opnieuw.');return;}
    win.document.open();win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${composedEsc(doc.name||'Samengesteld document')}</title><style>${printStyles()}</style></head><body class="composed-document">${documentHtml(doc)}<script>window.onload=()=>{let done=false;const go=()=>{if(done)return;done=true;setTimeout(()=>window.print(),80)};const imgs=[...document.images];Promise.all(imgs.map(img=>img.complete?Promise.resolve():new Promise(resolve=>{img.addEventListener('load',resolve,{once:true});img.addEventListener('error',resolve,{once:true})}))).then(go);setTimeout(go,6000)}<\/script></body></html>`);win.document.close();
  };

  async function composedHistoryPdfImageData(src){
    if(!src||composedHistoryIsVideo(src))return null;let objectUrl='';
    try{
      let imageSrc=src;
      if(!String(src).startsWith('data:image/')){const response=await fetch(src,{credentials:'same-origin',cache:'no-store'});if(!response.ok)throw new Error(`foto HTTP ${response.status}`);objectUrl=URL.createObjectURL(await response.blob());imageSrc=objectUrl;}
      const image=await new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=reject;img.src=imageSrc;});
      const max=1500,scale=Math.min(1,max/Math.max(image.naturalWidth||1,image.naturalHeight||1)),canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round((image.naturalWidth||1)*scale));canvas.height=Math.max(1,Math.round((image.naturalHeight||1)*scale));const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0,canvas.width,canvas.height);return {data:canvas.toDataURL('image/jpeg',0.82),width:canvas.width,height:canvas.height};
    }catch(error){console.warn('[Machinepark] verslagfoto kon niet in samengestelde PDF',error);return null;}finally{if(objectUrl)URL.revokeObjectURL(objectUrl);}
  }
  createComposedPdfFile=async function(doc){
    const JsPDF=await loadJsPdf(),pdf=new JsPDF({unit:'mm',format:'a4',orientation:'portrait',compress:true}),s=doc.snapshot||{devices:[],maintenance:[],breakdowns:[],parts:[]},groups=composedHistoryRows(s),margin=14,maxY=282,width=182;let y=20,page=1;
    const header=()=>{pdf.setFont('helvetica','bold');pdf.setFontSize(15);pdf.text(pdfSafe(doc.name||'Samengesteld document'),margin,11);pdf.setFont('helvetica','normal');pdf.setFontSize(7);pdf.text(`Pagina ${page}`,196,11,{align:'right'});pdf.line(margin,14,196,14);y=20;};
    const newPage=()=>{pdf.addPage();page+=1;header();};
    const write=(text,size=8.5,bold=false,indent=0,space=1)=>{const clean=pdfSafe(text||' ');pdf.setFont('helvetica',bold?'bold':'normal');pdf.setFontSize(size);const lines=pdf.splitTextToSize(clean,width-indent);const height=Math.max(1,lines.length)*(size*0.43)+space;if(y+height>maxY)newPage();pdf.text(lines,margin+indent,y);y+=height;};
    const addPhotos=async photos=>{for(let i=0;i<photos.length;i+=2){const pair=[];for(const src of photos.slice(i,i+2)){const data=await composedHistoryPdfImageData(src);if(data)pair.push(data);}if(!pair.length)continue;const rowMax=57;if(y+rowMax+5>maxY)newPage();let tallest=0;pair.forEach((img,index)=>{const boxW=87,boxH=55,ratio=img.width/img.height;let w=boxW,h=w/ratio;if(h>boxH){h=boxH;w=h*ratio;}const x=margin+index*91+(boxW-w)/2;pdf.addImage(img.data,'JPEG',x,y,w,h,undefined,'FAST');tallest=Math.max(tallest,h);});y+=tallest+5;}};
    header();write(`Vastgelegd: ${composedDate(s.capturedAt||doc.createdAt)} | Opgeslagen door: ${doc.createdBy||'—'}`,8,false);write(`Toestellen: ${(s.devices||[]).length}`,8,false);write('CHRONOLOGISCHE GESCHIEDENIS PER LOCATIE - NIEUWSTE EERST',11,true,0,3);
    for(const group of groups){write(group.location,10.5,true,0,2);for(const event of group.events){write(`${composedDate(event.moment)} | ${event.kind}`,9,true,2,1);const devices=[...(event.devices||[])];if(devices.length)write(`Toestel(len): ${devices.join(', ')}`,8,false,4,1);const tech=[...(event.technicians||[])];if(tech.length)write(`Technieker: ${tech.join(', ')}`,8,false,4,1);if(event.rows?.length){for(const row of event.rows){const device=(s.devices||[]).find(item=>item.id===row.item?.deviceId);write(`${row.kind} | ${composedHistoryDeviceLabel(device)}`,8.5,true,5,1);write(recordDescription(row.kind,row.item),8,false,7,1);const parts=composedHistoryPartsText(s,row.item);if(parts)write(`Onderdelen: ${parts}`,7.5,false,7,1);}}else if(event.details)write(event.details,8,false,5,1);await addPhotos(composedHistoryPhotoList(event.rows));y+=2;}}
    const allParts=mergedAllParts(s);write('TOTAAL GEBRUIKTE ONDERDELEN',10.5,true,0,2);if(!allParts.length)write('Geen onderdelen geregistreerd.',8,false);else allParts.forEach(part=>write(`${part.code} | ${part.description} | totaal ${part.qty} | ${part.devices.join(', ')}`,8,false));
    const blob=pdf.output('blob'),safe=String(doc.name||'Samengesteld_document').replace(/[\\/:*?"<>|]+/g,'-').replace(/\s+/g,'_').slice(0,100);return new File([blob],`${safe||'Samengesteld_document'}.pdf`,{type:'application/pdf'});
  };

'''
    index = index.replace(anchor, script + anchor, 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'Chronologische geschiedenis per locatie',
    "kind:'Serviceverslag'",
    'composedHistoryPhotoList(rows)',
    "events.sort((a,b)=>String(b.moment||'').localeCompare(String(a.moment||'')))",
    'data-photo-lightbox',
    "fetch(src,{credentials:'same-origin',cache:'no-store'})",
    "pdf.addImage(img.data,'JPEG'",
    'Promise.all(imgs.map',
    'Foto’s staan bij het bijbehorende verslag.',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: geschiedenis/foto-token ontbreekt: {needle}')

print('[Machinepark] samengesteld overzicht toont per locatie nieuwste geschiedenis eerst met alle verslagfoto’s bij het juiste verslag')
