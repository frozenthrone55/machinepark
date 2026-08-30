# Machinepark DEVELOPMENT

Deze branch is bedoeld voor online testen via de Netlify Deploy Preview, zonder production `main` te wijzigen.

## Branches en deploy
- Ontwikkeling: `development`
- Productie: `main`
- PR #1 blijft de releasekandidaat van `development` naar `main`.
- Merge pas naar `main` nadat de preview functioneel is gecontroleerd en daar expliciet opdracht voor is gegeven.

## Gedeelde centrale gegevens
Development en production gebruiken bewust dezelfde centrale Netlify Blobs-store: `machinepark-central`.
Daardoor zijn wijzigingen aan echte Machinepark-data en Clerk-gebruikers in de preview ook echte gedeelde wijzigingen.

## Authenticatie en rollen
- Clerk verzorgt de aanmelding.
- Gedeelde serverauthenticatie en serverconfig staan in `netlify/functions/_shared/server-auth.mjs`.
- De vaste hoofdbeheerder behoudt altijd alle rechten.
- Rollen en rechten zijn configureerbaar in Beheer.
- Rechten op mutaties worden server-side gecontroleerd.
- Een rol wordt pas verwijderd nadat alle Clerk-gebruikers gepagineerd zijn gecontroleerd op gebruik van die rol.
- Secrets horen alleen in Netlify Environment Variables en nooit in GitHub.

## Foto-opslag
- Toestellen: maximaal 5 foto’s, één selecteerbare overzichtsfoto.
- Onderhoud en depannages: maximaal 5 foto’s per verslag.
- Toestel-, onderdeel-, onderhouds- en depannagefoto’s gebruiken aparte Netlify Blob-opslag in plaats van zware afbeeldingsdata in de centrale JSON-snapshot.
- Bestaande oude foto’s worden tijdens rustige momenten op de achtergrond naar de nieuwe opslag gemigreerd.
- Overzichten gebruiken thumbnails en lazy loading; volledige foto’s blijven beschikbaar voor details, vergroten, afdrukken en export waar van toepassing.
- Thumbnailgeneratie gebeurt buiten het kritieke opslagpad zodat foto’s opslaan vlot blijft.
- Bij verwijderen van een foto of een volledige foto-eigenaar worden originele Blob-bestanden én thumbnails opgeruimd.
- Logboekherstel zet bewust geen verwijzingen terug naar foto’s die definitief verwijderd zijn.

## Frontend-build
De oorspronkelijke applicatie blijft compatibel met de bestaande `index.html`, maar de tijdens de build toegevoegde featurelaag wordt na alle patches automatisch opgesplitst:
- `assets/machinepark-build.js` bevat de gegenereerde feature-JavaScript;
- `assets/machinepark-build.css` bevat de gegenereerde feature-CSS;
- `scripts/extract-build-assets.py` voert deze finalisatie uit en bewaart buildmarkers voor idempotente builds.

De service worker cachet deze assets mee. Hierdoor blijft `index.html` kleiner en is de featurelaag beter controleerbaar.

## Kwaliteitscontrole
`npm test` voert achtereenvolgens uit:
1. de volledige build;
2. `scripts/audit-codebase.py` voor structurele codecontrole;
3. de automatische Node-tests.

`npm run check:functions` controleert alle Netlify JavaScript-modules, inclusief `_shared`, op syntax.

De code-audit bewaakt onder meer:
- ongebruikte of ontbrekende `build-*.py`-bestanden;
- dubbele buildstappen en buildmarkers;
- niet-gecontroleerde Netlify-modules;
- ongebruikte package dependencies;
- consistente fotolimieten en Blob-opslag;
- gedeelde Clerk-authenticatie/serverconfig;
- externe frontend-assets;
- aansluiting van de service-worker cacheversie op de appversie;
- te veel opeenvolgende runtime-wrappers op kernfuncties.

## Werkwijze
1. Ontwikkel uitsluitend op `development`.
2. Laat functiesyntaxis, build, audit en tests slagen.
3. Controleer de Netlify Deploy Preview op desktop en mobiel.
4. Merge pas naar `main` na expliciete goedkeuring.
