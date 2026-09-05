# Machinepark – Synology self-host test

Deze branch is een aparte proefversie. De huidige Netlify-versie op `development` blijft ongewijzigd en werkend.

## Doel

Machinepark stap voor stap lokaal op een Synology DS1813+ laten draaien via Web Station, zodat gegevens, foto's, handleidingen en uiteindelijk ook gebruikersbeheer lokaal beheerd kunnen worden.

## Belangrijke regel

We vervangen niets in één keer. Elke migratiestap moet eerst lokaal werken voordat de volgende internetafhankelijke functie wordt vervangen.

## Fasen

1. **Web Station/PHP controleren**
   - kopieer de map `synology` naar de webmap van de NAS;
   - open `synology/health.php`;
   - controleer of JSON met `"ok": true` verschijnt.

2. **Frontend lokaal openen**
   - huidige statische Machinepark-bestanden op de NAS plaatsen;
   - nog zonder de bestaande productieversie te wijzigen.

3. **Centrale gegevens lokaal opslaan**
   - Netlify centrale data vervangen door een lokale API;
   - opslag in een map buiten de publieke webmap;
   - bestandlocking/transacties zodat twee gebruikers elkaar niet overschrijven.

4. **Foto's en handleidingen lokaal**
   - toestel-foto's;
   - servicefoto's;
   - handleidingen;
   - andere uploads.

5. **Lokale gebruikers en rollen**
   - huidige rolregels behouden;
   - externe login pas vervangen nadat de lokale opslag stabiel is.

6. **Volledig zelfstandig**
   - geen Netlify Functions/Blobs meer nodig;
   - geen externe login meer nodig;
   - alleen de Synology + browserclients.

## Voorgestelde NAS-mappen

De webapp:

```
/volume1/web/machinepark/
```

Privégegevens buiten de webroot:

```
/volume1/MachineparkData/
  data/
  photos/
  manuals/
  uploads/
  backups/
```

De uiteindelijke API mag nooit rechtstreeks willekeurige bestanden uit `MachineparkData` publiceren. Bestanden worden alleen via gecontroleerde endpoints gelezen/geschreven.

## Veiligheid

De DS1813+ is oudere hardware. Voor de eerste test gebruiken we de app alleen op het lokale netwerk. We zetten geen routerpoorten open. Externe toegang bekijken we pas wanneer de lokale versie stabiel is.

## Eerste test

Plaats `synology/health.php` onder Web Station en open het via de browser. Een succesvolle respons ziet er ongeveer zo uit:

```json
{
  "ok": true,
  "app": "Machinepark",
  "storage": {
    "baseDirConfigured": false
  }
}
```

Daarna bouwen we de eerste lokale data-API.


## Opslagtest

Na het aanmaken van de mappen onder `/volume1/MachineparkData`, kopieer ook:

```
synology/storage-test.php
```

naar:

```
/volume1/web/machinepark/synology/storage-test.php
```

Open daarna in de browser:

```
http://<NAS-IP>/machinepark/synology/storage-test.php
```

De test:
- controleert of alle lokale mappen bestaan;
- controleert lees- en schrijfrechten;
- maakt tijdelijk `data/_machinepark_write_test.json`;
- leest het bestand terug;
- verwijdert het bestand daarna meteen weer.

Bij een correcte configuratie staat bovenaan `"ok": true`.

