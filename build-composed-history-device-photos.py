from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / 'index.html'
FEATURE_MARKER = 'data-machinepark-build-fix="composed-history-photos-v1"'
MARKER = 'data-machinepark-build-fix="composed-history-device-photos-v1"'

index = INDEX.read_text(encoding='utf-8')
if FEATURE_MARKER not in index:
    raise SystemExit('Buildvalidatie mislukt: geschiedenis/foto-overzicht ontbreekt voor toestel-fotokoppeling')

if MARKER not in index:
    anchor = '  function openComposedPreview(doc)'
    if index.count(anchor) != 1:
        raise SystemExit(f'Buildvalidatie mislukt: verwacht 1x preview-anker voor toestel-fotokoppeling, gevonden {index.count(anchor)}x')

    script = r'''
  composedHistoryWorkHtml=function(snapshot,row){
    const record=row.item||{},device=(snapshot.devices||[]).find(item=>item.id===record.deviceId),parts=composedHistoryPartsText(snapshot,record),tech=record.technician||record.serviceVisitTechnician||record.serviceReportTechnician||'—';
    const deviceLabel=composedHistoryDeviceLabel(device),photos=composedHistoryPhotosHtml([row],`${row.kind} ${deviceLabel}`);
    return `<div class="composed-history-work"><div class="composed-history-work-head">${composedEsc(row.kind)} · ${composedEsc(deviceLabel)}</div><div class="composed-history-work-detail">${composedEsc(recordDescription(row.kind,record))}</div><div class="composed-history-meta"><span><strong>Technieker:</strong> ${composedEsc(tech)}</span></div>${parts?`<div class="composed-history-work-parts"><strong>Onderdelen:</strong> ${composedEsc(parts)}</div>`:''}${photos}</div>`;
  };

  composedHistoryEventHtml=function(snapshot,event){
    const rows=event.rows||[],technicians=[...(event.technicians||[])],devices=[...(event.devices||[])];
    const details=rows.length?rows.map(row=>composedHistoryWorkHtml(snapshot,row)).join(''):`<div class="composed-history-work-detail">${composedEsc(event.details||'Locatie geregistreerd.')}</div>`;
    return `<article class="composed-history-event"><div class="composed-history-event-head"><div><div class="composed-history-event-title"><span class="badge">${composedEsc(event.kind)}</span><strong>${composedEsc(devices.join(', ')||'—')}</strong></div><div class="composed-history-meta">${technicians.length?`<span><strong>Technieker:</strong> ${composedEsc(technicians.join(', '))}</span>`:''}</div></div><div class="composed-history-date">${composedEsc(composedDate(event.moment))}</div></div>${details}</article>`;
  };

  createComposedPdfFile=async function(doc){
    const JsPDF=await loadJsPdf(),pdf=new JsPDF({unit:'mm',format:'a4',orientation:'portrait',compress:true}),s=doc.snapshot||{devices:[],maintenance:[],breakdowns:[],parts:[]},groups=composedHistoryRows(s),margin=14,maxY=282,width=182;let y=20,page=1;
    const header=()=>{pdf.setFont('helvetica','bold');pdf.setFontSize(15);pdf.text(pdfSafe(doc.name||'Samengesteld document'),margin,11);pdf.setFont('helvetica','normal');pdf.setFontSize(7);pdf.text(`Pagina ${page}`,196,11,{align:'right'});pdf.line(margin,14,196,14);y=20;};
    const newPage=()=>{pdf.addPage();page+=1;header();};
    const write=(text,size=8.5,bold=false,indent=0,space=1)=>{const clean=pdfSafe(text||' ');pdf.setFont('helvetica',bold?'bold':'normal');pdf.setFontSize(size);const lines=pdf.splitTextToSize(clean,width-indent);const height=Math.max(1,lines.length)*(size*0.43)+space;if(y+height>maxY)newPage();pdf.text(lines,margin+indent,y);y+=height;};
    const addPhotos=async photos=>{for(let i=0;i<photos.length;i+=2){const pair=[];for(const src of photos.slice(i,i+2)){const data=await composedHistoryPdfImageData(src);if(data)pair.push(data);}if(!pair.length)continue;const rowMax=57;if(y+rowMax+5>maxY)newPage();let tallest=0;pair.forEach((img,index)=>{const boxW=87,boxH=55,ratio=img.width/img.height;let w=boxW,h=w/ratio;if(h>boxH){h=boxH;w=h*ratio;}const x=margin+index*91+(boxW-w)/2;pdf.addImage(img.data,'JPEG',x,y,w,h,undefined,'FAST');tallest=Math.max(tallest,h);});y+=tallest+5;}};
    header();write(`Vastgelegd: ${composedDate(s.capturedAt||doc.createdAt)} | Opgeslagen door: ${doc.createdBy||'—'}`,8,false);write(`Toestellen: ${(s.devices||[]).length}`,8,false);write('CHRONOLOGISCHE GESCHIEDENIS PER LOCATIE - NIEUWSTE EERST',11,true,0,3);
    for(const group of groups){
      write(group.location,10.5,true,0,2);
      for(const event of group.events){
        write(`${composedDate(event.moment)} | ${event.kind}`,9,true,2,1);
        const devices=[...(event.devices||[])];if(devices.length)write(`Toestel(len): ${devices.join(', ')}`,8,false,4,1);
        const tech=[...(event.technicians||[])];if(tech.length)write(`Technieker: ${tech.join(', ')}`,8,false,4,1);
        if(event.rows?.length){
          for(const row of event.rows){
            const device=(s.devices||[]).find(item=>item.id===row.item?.deviceId);
            write(`${row.kind} | ${composedHistoryDeviceLabel(device)}`,8.5,true,5,1);
            write(recordDescription(row.kind,row.item),8,false,7,1);
            const parts=composedHistoryPartsText(s,row.item);if(parts)write(`Onderdelen: ${parts}`,7.5,false,7,1);
            await addPhotos(composedHistoryPhotoList([row]));
          }
        }else if(event.details)write(event.details,8,false,5,1);
        y+=2;
      }
    }
    const allParts=mergedAllParts(s);write('TOTAAL GEBRUIKTE ONDERDELEN',10.5,true,0,2);if(!allParts.length)write('Geen onderdelen geregistreerd.',8,false);else allParts.forEach(part=>write(`${part.code} | ${part.description} | totaal ${part.qty} | ${part.devices.join(', ')}`,8,false));
    const blob=pdf.output('blob'),safe=String(doc.name||'Samengesteld_document').replace(/[\\/:*?"<>|]+/g,'-').replace(/\s+/g,'_').slice(0,100);return new File([blob],`${safe||'Samengesteld_document'}.pdf`,{type:'application/pdf'});
  };
'''
    index = index.replace(anchor, script + '\n' + anchor, 1)
    index = index.replace('</head>', f'<meta {MARKER}>\n</head>', 1)
    INDEX.write_text(index, encoding='utf-8')

built = INDEX.read_text(encoding='utf-8')
required = [
    MARKER,
    'composedHistoryPhotosHtml([row]',
    'const details=rows.length?rows.map(row=>composedHistoryWorkHtml(snapshot,row)).join',
    'await addPhotos(composedHistoryPhotoList([row]));',
]
for needle in required:
    if needle not in built:
        raise SystemExit(f'Buildvalidatie mislukt: toestel-fotokoppeling ontbreekt: {needle}')

print('[Machinepark] foto’s in samengestelde geschiedenis blijven bij het juiste toestel per verslag')
