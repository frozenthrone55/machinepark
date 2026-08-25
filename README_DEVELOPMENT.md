# Machinepark DEVELOPMENT

Deze branch is bedoeld voor online testen via de Netlify branch deploy `development`, zonder production deploys op `main`.

## Online development
- Branch: `development`
- Verwachte Netlify-URL: `https://development--machinepark.netlify.app`
- Branch deploys kosten geen production deploy-credits.
- Webrequests, bandbreedte en Functions kunnen nog wel beperkt metered usage veroorzaken.

## Gedeelde centrale gegevens
Development en production gebruiken bewust dezelfde centrale Netlify Blobs-store: `machinepark-central`.
Daardoor zijn wijzigingen in development ook zichtbaar in production en omgekeerd.

## Clerk Development
Gebruik voor deze omgeving alleen Clerk Development keys:
- `CLERK_PUBLISHABLE_KEY` = `pk_test_...`
- `CLERK_SECRET_KEY` = `sk_test_...`

Zet secrets alleen in Netlify Environment Variables en nooit in GitHub.

## Huidige releasefuncties
- Machinepark branding + favicon/PWA-icoon
- verbeterde globale zoekfuncties
- buiten-dienst toestellen alleen zichtbaar in zoeken op Toestellen
- beheerder/gebruiker-rollen
- gebruikers uitnodigen, bewerken en verwijderen
- scrollbaar wijzigingslogboek voor beheerder
- manuele halfjaarlijkse en jaarlijkse onderhoudsplanning

## Werkwijze
1. Ontwikkel en test eerst op `development`.
2. Controleer de development-site op pc en iPhone.
3. Merge pas naar `main` wanneer de versie goed werkt.
