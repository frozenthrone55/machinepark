from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# De echte prijslijst gebruikt o.a. "Prijs excl. BTW". Herken die expliciet.
old_price_idx = "price:findHeaderIndex(headers,['prijs','prijs euro','price']),"
new_price_idx = "price:findHeaderIndex(headers,['Prijs excl. BTW','Prijs excl BTW','Prijs exclusief BTW','Prijs ex BTW','prijs','prijs euro','price']),"
if old_price_idx in s:
    s = s.replace(old_price_idx, new_price_idx, 1)
elif new_price_idx not in s:
    raise SystemExit('Prijskolomkoppeling kon niet worden uitgebreid')

# De aangeleverde prijslijst gebruikt ook de eenvoudige kolomnaam "Locatie".
old_warehouse_idx = "warehouse:findHeaderIndex(headers,['Magazijnlocatie','magazijn locatie','warehouse']),"
new_warehouse_idx = "warehouse:findHeaderIndex(headers,['Magazijnlocatie','magazijn locatie','Locatie','warehouse']),"
if old_warehouse_idx in s:
    s = s.replace(old_warehouse_idx, new_warehouse_idx, 1)

# De prijskolom is verplicht: de import is de bron van waarheid voor prijzen.
old_idx_end = " minStock:findHeaderIndex(headers,['Minimumvoorraad','minimum voorraad','min voorraad'])\n};const existing=new Map(state.parts.map(p=>[cleanCell(p.artNr).toLowerCase(),p]));"
new_idx_end = " minStock:findHeaderIndex(headers,['Minimumvoorraad','minimum voorraad','min voorraad'])\n};if(idx.price<0)throw new Error('Prijskolom niet gevonden. Verwacht bijvoorbeeld “Prijs excl. BTW” of “prijs”.');const existing=new Map(state.parts.map(p=>[cleanCell(p.artNr).toLowerCase(),p]));"
if old_idx_end in s:
    s = s.replace(old_idx_end, new_idx_end, 1)
elif "if(idx.price<0)throw new Error('Prijskolom niet gevonden." not in s:
    raise SystemExit('Controle op verplichte prijskolom kon niet worden toegevoegd')

# Bij bestaande onderdelen mag een negatieve/ongeldige stock de prijsupdate nooit blokkeren.
old_stock_logic = "if(stockNum!==null&&stockNum<0){records.push({artNr,key,action:'skip',reason:'Negatieve voorraad',stock:null});continue}if(old&&stockNum===null){records.push({artNr,key,action:'skip',reason:'Geen geldig aantal — bestaande voorraad behouden',stock:null});continue}const stock=stockNum===null?0:Math.round(stockNum);"
new_stock_logic = "if(!old&&stockNum!==null&&stockNum<0){records.push({artNr,key,action:'skip',reason:'Negatieve voorraad bij nieuw onderdeel',stock:null});continue}const stock=old&&(stockNum===null||stockNum<0)?Number(old.stock||0):(stockNum===null?0:Math.round(stockNum));"
if old_stock_logic in s:
    s = s.replace(old_stock_logic, new_stock_logic, 1)
elif new_stock_logic not in s:
    raise SystemExit('Stocklogica kon niet worden losgekoppeld van prijsupdate')

# Elke verwerkte artikelregel moet een geldige actuele prijs hebben.
old_get = "const get=(k)=>idx[k]>=0?cleanCell(row[idx[k]]):'';if(old){"
new_get = "const get=(k)=>idx[k]>=0?cleanCell(row[idx[k]]):'';const importedPrice=flexibleNumber(row[idx.price]);if(importedPrice===null)throw new Error('Geen geldige prijs voor artikel '+artNr+'. Controleer de kolom Prijs excl. BTW.');if(old){"
if old_get in s:
    s = s.replace(old_get, new_get, 1)
elif "Controleer de kolom Prijs excl. BTW." not in s:
    raise SystemExit('Prijsvalidatie per artikel kon niet worden toegevoegd')

# Bestaande onderdelen: importprijs overschrijft altijd de huidige prijs.
old_plan_v147 = "if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||''})}"
old_plan_v148 = "if(old){const importedDeviceBrand=get('deviceBrand'),importedPrice=idx.price>=0?flexibleNumber(row[idx.price]):null;records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||'',newPrice:importedPrice===null?Number(old.price||0):importedPrice})}"
new_plan = "if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||'',newPrice:importedPrice})}"
if old_plan_v148 in s:
    s = s.replace(old_plan_v148, new_plan, 1)
elif old_plan_v147 in s:
    s = s.replace(old_plan_v147, new_plan, 1)
elif "newPrice:importedPrice" not in s:
    raise SystemExit('Prijsupdate in stocktelling kon niet worden ingesteld')

old_apply_plain = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',updatedAt:new Date().toISOString()});"
old_apply_price = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice??Number(r.old.price||0),updatedAt:new Date().toISOString()});"
new_apply = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice,updatedAt:new Date().toISOString()});"
if old_apply_price in s:
    s = s.replace(old_apply_price, new_apply, 1)
elif old_apply_plain in s:
    s = s.replace(old_apply_plain, new_apply, 1)
elif "price:r.newPrice,updatedAt" not in s:
    raise SystemExit('Opslaan van importprijs kon niet worden ingesteld')

# Laat in de controlepreview zichtbaar zien dat de prijs werkelijk wijzigt.
old_head = '<thead><tr><th>Art nr</th><th>Actie</th><th>Oude voorraad</th><th>Nieuwe voorraad</th></tr></thead>'
new_head = '<thead><tr><th>Art nr</th><th>Actie</th><th>Oude voorraad</th><th>Nieuwe voorraad</th><th>Oude prijs</th><th>Nieuwe prijs</th></tr></thead>'
s = s.replace(old_head, new_head, 1)
old_row = "<td>${r.action==='update'?Number(r.old.stock||0):'—'}</td><td><strong>${r.action==='update'?r.newStock:r.newPart.stock}</strong></td>"
new_row = "<td>${r.action==='update'?Number(r.old.stock||0):'—'}</td><td><strong>${r.action==='update'?r.newStock:r.newPart.stock}</strong></td><td>${r.action==='update'?'€ '+Number(r.old.price||0).toFixed(2):'—'}</td><td><strong>€ ${Number(r.action==='update'?r.newPrice:r.newPart.price).toFixed(2)}</strong></td>"
if old_row in s:
    s = s.replace(old_row, new_row, 1)
# colspan voor de extra twee prijskolommen
s = s.replace('colspan="4" class="muted">… en nog ${records.length-25} regels', 'colspan="6" class="muted">… en nog ${records.length-25} regels', 1)

old_help1 = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Een geldige geïmporteerde prijs vervangt altijd de bestaande prijs van het onderdeel. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
old_help2 = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
new_help = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Prijs excl. BTW uit het importbestand vervangt altijd de bestaande onderdeelprijs. Bij een bestaande artikelregel met een ongeldige of negatieve voorraad blijft de huidige voorraad behouden, maar de prijs wordt wel bijgewerkt.'
if old_help1 in s:
    s = s.replace(old_help1, new_help, 1)
elif old_help2 in s:
    s = s.replace(old_help2, new_help, 1)

for old_version in [
    'v1.49 • Importprijzen zijn leidend',
    'v1.48 • Prijzen bij stocktelling',
    'v1.47 • Categorie bij stocktelling',
    'v1.46 • Alleen actieve toestellen'
]:
    s = s.replace(old_version, 'v1.50 • Prijsimport hersteld', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.49-import-prices-authoritative',
    'machinepark-v1.48-stock-prices',
    'machinepark-v1.47-stock-category',
    'machinepark-v1.46-active-devices-only'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.50-stock-price-fix')
sw.write_text(ws, encoding='utf-8')
