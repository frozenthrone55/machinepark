from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

# De prijskolom is verplicht: de stocktelling is voortaan de bron van waarheid voor prijzen.
old_idx_end = " minStock:findHeaderIndex(headers,['Minimumvoorraad','minimum voorraad','min voorraad'])\n};const existing=new Map(state.parts.map(p=>[cleanCell(p.artNr).toLowerCase(),p]));"
new_idx_end = " minStock:findHeaderIndex(headers,['Minimumvoorraad','minimum voorraad','min voorraad'])\n};if(idx.price<0)throw new Error('Kolom “prijs” niet gevonden. De geïmporteerde prijslijst moet de actuele prijzen bevatten.');const existing=new Map(state.parts.map(p=>[cleanCell(p.artNr).toLowerCase(),p]));"
if old_idx_end in s:
    s = s.replace(old_idx_end, new_idx_end, 1)
elif "if(idx.price<0)throw new Error('Kolom “prijs” niet gevonden." not in s:
    raise SystemExit('Controle op verplichte prijskolom kon niet worden toegevoegd')

# Elke artikelregel moet een geldige prijs bevatten; zo kan nooit stilzwijgend een oude prijs blijven staan.
old_get = "const get=(k)=>idx[k]>=0?cleanCell(row[idx[k]]):'';if(old){"
new_get = "const get=(k)=>idx[k]>=0?cleanCell(row[idx[k]]):'';const importedPrice=flexibleNumber(row[idx.price]);if(importedPrice===null)throw new Error('Geen geldige prijs voor artikel '+artNr+'. Alle geïmporteerde artikelen moeten een actuele prijs bevatten.');if(old){"
if old_get in s:
    s = s.replace(old_get, new_get, 1)
elif "Alle geïmporteerde artikelen moeten een actuele prijs bevatten." not in s:
    raise SystemExit('Prijsvalidatie per artikel kon niet worden toegevoegd')

old_plan = "if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||''})}"
old_plan_v148 = "if(old){const importedDeviceBrand=get('deviceBrand'),importedPrice=idx.price>=0?flexibleNumber(row[idx.price]):null;records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||'',newPrice:importedPrice===null?Number(old.price||0):importedPrice})}"
new_plan = "if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||'',newPrice:importedPrice})}"
if old_plan_v148 in s:
    s = s.replace(old_plan_v148, new_plan, 1)
elif old_plan in s:
    s = s.replace(old_plan, new_plan, 1)
elif "newPrice:importedPrice" not in s:
    raise SystemExit('Prijsupdate in stocktelling kon niet strikt worden ingesteld')

old_apply = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',updatedAt:new Date().toISOString()});"
old_apply_v148 = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice??Number(r.old.price||0),updatedAt:new Date().toISOString()});"
new_apply = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice,updatedAt:new Date().toISOString()});"
if old_apply_v148 in s:
    s = s.replace(old_apply_v148, new_apply, 1)
elif old_apply in s:
    s = s.replace(old_apply, new_apply, 1)
elif "price:r.newPrice,updatedAt" not in s:
    raise SystemExit('Opslaan van de leidende importprijs kon niet worden ingesteld')

old_help = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
old_help_v148 = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Een geldige geïmporteerde prijs vervangt altijd de bestaande prijs van het onderdeel. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
new_help = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. De geïmporteerde prijs vervangt altijd de bestaande prijs van het onderdeel; de prijskolom en een geldige prijs per artikel zijn daarom verplicht.'
if old_help_v148 in s:
    s = s.replace(old_help_v148, new_help, 1)
elif old_help in s:
    s = s.replace(old_help, new_help, 1)

for old_version in [
    'v1.48 • Prijzen bij stocktelling',
    'v1.47 • Categorie bij stocktelling',
    'v1.46 • Alleen actieve toestellen',
    'v1.45 • Toestellen autocomplete',
    'v1.44 • Onderdelen autocomplete'
]:
    s = s.replace(old_version, 'v1.49 • Importprijzen zijn leidend', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.48-stock-prices',
    'machinepark-v1.47-stock-category',
    'machinepark-v1.46-active-devices-only',
    'machinepark-v1.45-device-autocomplete',
    'machinepark-v1.44-parts-autocomplete'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.49-import-prices-authoritative')
sw.write_text(ws, encoding='utf-8')
