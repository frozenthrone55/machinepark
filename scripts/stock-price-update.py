from pathlib import Path

p = Path('index.html')
s = p.read_text(encoding='utf-8')

old_plan = "if(old){const importedDeviceBrand=get('deviceBrand');records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||''})}"
new_plan = "if(old){const importedDeviceBrand=get('deviceBrand'),importedPrice=idx.price>=0?flexibleNumber(row[idx.price]):null;records.push({artNr,key,action:'update',old,newStock:stock,newDeviceBrand:importedDeviceBrand||old.deviceBrand||'',newPrice:importedPrice===null?Number(old.price||0):importedPrice})}"
if old_plan in s:
    s = s.replace(old_plan, new_plan, 1)
elif "newPrice:importedPrice===null?Number(old.price||0):importedPrice" not in s:
    raise SystemExit('Prijsupdate in stocktelling kon niet worden toegevoegd')

old_apply = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',updatedAt:new Date().toISOString()});"
new_apply = "for(const r of updates)await put('parts',{...r.old,stock:r.newStock,deviceBrand:r.newDeviceBrand??r.old.deviceBrand??'',price:r.newPrice??Number(r.old.price||0),updatedAt:new Date().toISOString()});"
if old_apply in s:
    s = s.replace(old_apply, new_apply, 1)
elif "price:r.newPrice??Number(r.old.price||0)" not in s:
    raise SystemExit('Opslaan van geïmporteerde prijs kon niet worden toegevoegd')

old_help = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
new_help = 'De kolom categorie wordt opgeslagen als Merk toestel bij Onderdelen en staat volledig los van het merk bij Toestellen. Een geldige geïmporteerde prijs vervangt altijd de bestaande prijs van het onderdeel. Alleen Art nr en Voorraad locatie 1 zijn vereist voor een stockupdate.'
if old_help in s:
    s = s.replace(old_help, new_help, 1)

for old_version in [
    'v1.47 • Categorie bij stocktelling',
    'v1.46 • Alleen actieve toestellen',
    'v1.45 • Toestellen autocomplete',
    'v1.44 • Onderdelen autocomplete'
]:
    s = s.replace(old_version, 'v1.48 • Prijzen bij stocktelling', 1)

p.write_text(s, encoding='utf-8')

sw = Path('sw.js')
ws = sw.read_text(encoding='utf-8')
for old_cache in [
    'machinepark-v1.47-stock-category',
    'machinepark-v1.46-active-devices-only',
    'machinepark-v1.45-device-autocomplete',
    'machinepark-v1.44-parts-autocomplete'
]:
    ws = ws.replace(old_cache, 'machinepark-v1.48-stock-prices')
sw.write_text(ws, encoding='utf-8')
