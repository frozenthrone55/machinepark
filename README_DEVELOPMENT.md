# Machinepark DEVELOPMENT

Deze branch is bedoeld voor online testen via de Netlify Deploy Preview, zonder production `main` te wijzigen.

## Branches en deploy
- Ontwikkeling: `development`
- Productie: `main`
- PR #1 blijft de releasekandidaat van `development` naar `main`.
- Merge pas naar `main` nadat de preview functioneel is gecontroleerd.

## Gedeelde centrale gegevens
Development en production gebruiken bewust dezelfde centrale Netlify Blobs-store: `machinepark-central`.
Daardoor zijn wijzigingen aan echte Machinepark-data en Clerk-gebruikers in de preview ook echte gedeelde wijzigingen.

## Authenticatie en rollen
- Clerk verzorgt de aanmelding.
- De vaste hoofdbeheerder behoudt altijd alle rechten.
- Rollen en rechten zijn configureerbaar in Beheer.
- Rechten op mutaties worden server-side gecontroleerd.
- `development` gebruikt dezelfde ingestelde Clerk/Netlify-omgeving als de deploy-preview; secrets horen alleen in Netlify Environment Variables en nooit in GitHub.

## Foto-opslag
- Toestellen: maximaal 5 foto’s, één selecteerbare overzichtsfoto.
- Onderdelen: foto’s worden apart opgeslagen.
- Toestel- en onderdeelfoto’s gebruiken Netlify Blobs in plaats van de centrale JSON-snapshot.
- Overzichten gebruiken thumbnails en lazy loading; volledige foto’s blijven beschikbaar voor details, vergroten, afdrukken en export waar van toepassing.
- Bij verwijderen van een foto, toestel of onderdeel worden ook de gekoppelde thumbnail/originele Blob-bestanden opgeruimd.
- Onderhouds- en depannageverslagfoto’s zitten voorlopig nog in de centrale snapshot; dit is een gekend schaalbaarheidspunt voor een latere migratie naar Blob-opslag.

## Kwaliteitscontrole
`npm test` voert achtereenvolgens uit:
1. de volledige build;
2. `scripts/audit-codebase.py` voor structurele codecontrole;
3. de automatische Node-tests.

`npm run check:functions` controleert alle top-level Netlify Functions op JavaScript-syntax.

De code-audit bewaakt onder meer:
- ongebruikte of ontbrekende `build-*.py`-bestanden;
- dubbele buildstappen en buildmarkers;
- niet-gecontroleerde Netlify Functions;
- ongebruikte package dependencies;
- consistente fotolimieten;
- aansluiting van de service-worker cacheversie op de appversie.

Onderhoudswaarschuwingen zijn bewust niet fataal. Ze markeren grotere refactors die afzonderlijk moeten worden getest, zoals het opsplitsen van de monolithische `index.html` en het centraliseren van gedeelde server-authenticatie.

## Werkwijze
1. Ontwikkel uitsluitend op `development`.
2. Laat functiesyntaxis, build, audit en tests slagen.
3. Controleer de Netlify Deploy Preview op desktop en mobiel.
4. Merge pas naar `main` na expliciete goedkeuring.
