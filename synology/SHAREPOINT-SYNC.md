## Lokale OneDrive-kopie (zonder Microsoft-appregistratie)

Als `/volume1/MachineparkData/config/sharepoint-sync.php` ontbreekt, gebruikt de module standaard `/volume1/MachineparkData/toestelsynchronisatie/koffiemachines inventaris 2025.xlsx`. Node.js wordt gezocht in de gebruikelijke Synology pakketpaden (16/18/20/22) en `/usr/local/bin/node`. PHP zip en dom en proc_open zijn nodig; curl en Microsoft-sleutels zijn bij deze route niet nodig.

1. Houd het bestaande SharePointbestand via OneDrive lokaal beschikbaar op de Windows-pc.
2. Maak de map `toestelsynchronisatie` in MachineparkData en plaats de eerste Excelkopie.
3. De scripts in `synology/windows` zijn afgestemd op Kris' bronpad en `\\192.168.0.200\MachineparkData`. Voer `install-device-excel-task.ps1` uit als de gewone Windows-gebruiker. De taak gebruikt de huidige aanmelding, draait elke 15 minuten en bij aanmelden. Geen wachtwoorden in scripts. Het log staat in `%LOCALAPPDATA%\MachineparkToestelsynchronisatie\copy.log`. De pc moet aanstaan, aangemeld zijn, OneDrive actueel en de NAS bereikbaar. Een slapende/afgemelde pc levert geen nieuwe bestanden.
4. Installeer Node.js 16 of hoger op de NAS en schakel PHP zip en dom in.
5. Maak in DSM Taakplanner een gebruikersscript dat elke 15 minuten draait met `php /volume1/web/machinepark/synology/sync-sharepoint-devices.php`. Kies de geïnstalleerde PHP 7.2 CLI als `php` niet in PATH zit. Het taakaccount moet de kopie kunnen lezen en MachineparkData kunnen schrijven.
6. Gebruik in Beheer eerst **Nu controleren** en controleer de historiek. Schakel daarna automatisch controleren in.

De Windows-taak schrijft een tijdelijk bestand en publiceert de complete kopie met een atomische vervanging. Machinepark gebruikt SHA-256 voor versiecontrole en controleert opnieuw na lezen. Alleen gewijzigde bytes worden geïmporteerd. De wijzigingshistoriek en laatste controle blijven in de bestaande serveropslag. Een mislukte import behoudt de vorige versie en toestellen. De getoonde bestandsdatum is de datum van de NAS-kopie, niet noodzakelijk de SharePoint-wijzigingsdatum.

Voor een afwijkend pad of Node-installatie kan het externe configuratiebestand dit bevatten:

```php
<?php
return [
    'source_mode' => 'local',
    'local_path' => '/volume1/MachineparkData/toestelsynchronisatie/koffiemachines inventaris 2025.xlsx',
    'node_path' => '/usr/local/bin/node',
];
```

# Automatische toestelsynchronisatie

Deze module leest het bestaande SharePoint-Excelbestand uitsluitend. Er zijn geen
Graph-aanroepen die het bestand schrijven, wijzigen of verwijderen. Het bestand
wordt gedownload omdat de Excel-workbook API geen applicatiemachtigingen ondersteunt.
De automatische taak gebruikt de planner én verwerking uit de handmatige
synchronisatie; de build genereert daarvan de Node-worker.

## Eenmalige installatie

1. Vraag IT om een Entra-app voor deze NAS met Microsoft Graph **Sites.Selected**
   (application), admin consent, en een expliciete **read**-toekenning op de site
   TechnischeDienst. Geef geen write/fullcontrol-recht. IT levert tenant-ID,
   client-ID, client secret, drive-ID en item-ID van het juiste bestand. De
   bestands-ID voorkomt afhankelijkheid van een tijdelijke deellink.
2. Controleer op de NAS een Node.js-uitvoerbaar bestand (>=16) en PHP 7.2 met
   curl, zip en dom. Node gebruikt geen npm-packages: het voert precies de
   bestaande JavaScript-importregels uit. Vul het bevestigde absolute pad in.
3. Kopieer `synology/sharepoint-sync.config.example.php` naar
   `/volume1/MachineparkData/config/sharepoint-sync.php`. Vul de gegevens daar
   lokaal in. Maak de map zo nodig aan, en beperk lezen tot de PHP-gebruiker en
   het account van de geplande taak. Deze configuratie ligt buiten de webroot
   en blijft behouden bij updates. Zet echte sleutels nooit in GitHub of chat.
4. Maak in DSM Taakplanner een gebruikersgedefinieerde taak, elke 15 minuten,
   met een account dat de Machinepark-data kan lezen en schrijven. Gebruik het
   **bevestigde** PHP 7.2 CLI-pad op jouw NAS, gevolgd door:
   `/volume1/web/machinepark/synology/sync-sharepoint-devices.php`.
   Het PHP CLI-pad moet dezelfde extensies hebben als PHP in Web Station.
5. Open **Beheer → Automatische toestelsynchronisatie**. Gebruik eerst **Nu
   controleren**, controleer de historiek, en schakel daarna automatisch
   controleren in. Zonder configuratie kan de schakelaar niet worden aangezet.
   De schakelaar alleen maakt geen DSM-taak aan.

Het juiste bestand is dat van deze gebruikerslink:
https://winecl.sharepoint.com/:x:/s/TechnischeDienst/IQDZiQhux2KiTq1XXV1trsQEAS8NAeFosmpd0gRXqABlj2U?e=IGzrGL

## Verwerking en historiek

- Eerste controle verwerkt het bestand; daarna alleen gewijzigde eTags.
- Het eerste numeriek gesorteerde werkblad en expliciete rode vulling worden
  op dezelfde manier gelezen als bij de bestaande handmatige XLSX-import.
- WCL-nummer is de sleutel. Locatie, merk/toestelgegevens, contractstart en
  rode statusmarkeringen volgen de bestaande importregels. Lege waarden
  wissen geen gegevens. Ontbrekende rijen verwijderen geen toestellen.
- Dubbele WCL-nummers of een ongeldige bron blokkeren de gehele synchronisatie.
- Microsoft-downloads gebeuren buiten de datalock. Tijdens verwerking wordt
  de nieuwste database geladen onder dezelfde lock als normale appwrites.
- Back-up, toestelwijzigingen, bronversie en historie worden samen atomair in
  state-v1.json opgeslagen. Oudere/offline clients kunnen de serverhistorie
  niet overschrijven. Service, foto's, ToDo, onderdelen en andere stores
  worden door deze taak niet gewijzigd.
- Historie wordt niet verwijderd; Beheer laadt 25 runs per pagina. Een
  ongewijzigde controle ververst alleen de laatste controletijd.
- Een mislukte download/import wordt gelogd en de bronversie wordt niet als
  verwerkt gemarkeerd: de volgende controle probeert opnieuw.
- Microsoft-toegang en de DSM-taak moeten op de echte omgeving worden getest.
  De paneelstatus bevestigt de configuratie, niet dat DSM de taak ingepland heeft.

Documentatie:
https://learn.microsoft.com/en-us/graph/api/driveitem-get-content?view=graph-rest-1.0
https://learn.microsoft.com/en-us/graph/permissions-selected-overview
https://learn.microsoft.com/en-us/graph/api/worksheet-list?view=graph-rest-1.0
