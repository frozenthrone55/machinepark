from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
MARKER = "machinepark-service-overview-work-search-v1"

index = INDEX.read_text(encoding="utf-8")

if MARKER not in index:
    old = r'''  function serviceOverviewApplyFilter(){
    var select=document.getElementById("serviceOverviewStatusFilter");
    var filter=select?select.value:"open";
    serviceOverviewRows().forEach(function(row){
      var status=(row.querySelector(".service-visit-status")||{}).textContent||"";
      status=status.trim();
      var open=status==="Open"||status==="In behandeling";
      row.style.display=filter==="all"?"":filter==="closed"?(open?"none":""):(open?"":"none");
    });
    var drafts=document.getElementById("serviceVisitDraftList");
    if(drafts)drafts.style.display=filter==="closed"?"none":"";
    var title=document.getElementById("pageTitle");
    if(state&&state.view==="service-overview"&&title)title.textContent=filter==="open"?"Open service":"Service";
  }'''

    new = r'''  // machinepark-service-overview-work-search-v1
  function serviceOverviewRecordMatchesWorkQuery(item,isMaintenance){
    if(!item)return false;
    try{
      if(isMaintenance&&typeof maintenanceMatchesQuery==="function"&&maintenanceMatchesQuery(item))return true;
      if(!isMaintenance&&typeof breakdownMatchesQuery==="function"&&breakdownMatchesQuery(item))return true;
    }catch(error){
      console.warn("[Machinepark] serviceverslag zoekmatch via werkzaamheden mislukt",error);
    }
    if(typeof searchIncludes!=="function")return false;
    var moment="";
    try{moment=typeof recordMoment==="function"?recordMoment(item):(item.date||"");}catch(_){moment=item.date||"";}
    var device="",parts="";
    try{device=typeof linkedDeviceSearchText==="function"?linkedDeviceSearchText(item.deviceId,moment):"";}catch(_){}
    try{parts=typeof linkedPartsSearchText==="function"?linkedPartsSearchText(item.usedParts||[]):"";}catch(_){}
    return searchIncludes([
      item.type,item.workTypeName,item.workType,item.description,item.issue,item.diagnosis,item.solution,
      item.notes,item.technician,item.priority,item.status,item.date,item.time,item.serviceVisitLocation,
      item.serviceReportTechnician,item.serviceVisitTechnician,device,parts
    ].join(" "));
  }

  function serviceOverviewWorkQueryMatches(row){
    if(!state||state.view!=="work")return true;
    if(!String(state.query||"").trim())return true;
    if(typeof searchIncludes==="function"&&searchIncludes(row.textContent||""))return true;
    var openButton=row.querySelector("[data-service-visit-open]");
    var reportId=openButton?String(openButton.dataset.serviceVisitOpen||""):"";
    if(!reportId)return false;
    var belongs=function(item){
      return !!item&&item.isDraft!==true&&!!item.serviceVisitId&&String(item.serviceReportId||item.serviceVisitId)===reportId;
    };
    if((state.maintenance||[]).some(function(item){return belongs(item)&&serviceOverviewRecordMatchesWorkQuery(item,true);})){return true;}
    return (state.breakdowns||[]).some(function(item){return belongs(item)&&serviceOverviewRecordMatchesWorkQuery(item,false);});
  }

  function serviceDraftWorkQueryMatches(row){
    if(!state||state.view!=="work")return true;
    if(!String(state.query||"").trim())return true;
    if(typeof searchIncludes==="function"&&searchIncludes(row.textContent||""))return true;
    var openButton=row.querySelector("[data-sv-draft-open]");
    var draftId=openButton?String(openButton.dataset.svDraftOpen||""):"";
    if(!draftId)return false;
    var belongs=function(item){return !!item&&item.isDraft===true&&(String(item.id||"")===draftId||String(item.draftBatchId||"")===draftId);};
    if((state.maintenance||[]).some(function(item){return belongs(item)&&serviceOverviewRecordMatchesWorkQuery(item,true);})){return true;}
    return (state.breakdowns||[]).some(function(item){return belongs(item)&&serviceOverviewRecordMatchesWorkQuery(item,false);});
  }

  function serviceOverviewApplyFilter(){
    var select=document.getElementById("serviceOverviewStatusFilter");
    var filter=select?select.value:"open";
    serviceOverviewRows().forEach(function(row){
      var status=(row.querySelector(".service-visit-status")||{}).textContent||"";
      status=status.trim();
      var open=status==="Open"||status==="In behandeling";
      var statusMatches=filter==="all"?true:filter==="closed"?!open:open;
      row.style.display=statusMatches&&serviceOverviewWorkQueryMatches(row)?"":"none";
    });
    var drafts=document.getElementById("serviceVisitDraftList");
    if(drafts){
      var draftsVisible=filter!=="closed";
      drafts.style.display=draftsVisible?"":"none";
      if(draftsVisible){
        Array.prototype.forEach.call(drafts.querySelectorAll(".service-draft-row"),function(row){
          row.style.display=serviceDraftWorkQueryMatches(row)?"":"none";
        });
      }
    }
    var title=document.getElementById("pageTitle");
    if(state&&state.view==="service-overview"&&title)title.textContent=filter==="open"?"Open service":"Service";
  }'''

    count = index.count(old)
    if count != 1:
        raise SystemExit(f"Buildvalidatie mislukt: serviceOverviewApplyFilter verwacht 1x, gevonden {count}")
    index = index.replace(old, new, 1)

required = [
    MARKER,
    "function serviceOverviewWorkQueryMatches(row)",
    "function serviceDraftWorkQueryMatches(row)",
    'state.view!=="work"',
    "maintenanceMatchesQuery(item)",
    "breakdownMatchesQuery(item)",
    'row.querySelector("[data-service-visit-open]")',
    'row.querySelector("[data-sv-draft-open]")',
    'statusMatches&&serviceOverviewWorkQueryMatches(row)',
]
for needle in required:
    if needle not in index:
        raise SystemExit("Buildvalidatie mislukt: zoekfilter serviceverslagen ontbreekt (" + needle + ")")

INDEX.write_text(index, encoding="utf-8")
print("[Machinepark] werkzaamhedenzoeker filtert ook serviceverslagen en serviceconcepten")
