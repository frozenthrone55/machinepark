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
