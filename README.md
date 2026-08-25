# Machinepark v1.23 — centrale synchronisatie

Machinepark wordt gehost via Netlify, gebruikt Clerk voor aanmelden en gebruikt Netlify Blobs als centrale opslag.

## Vereiste Netlify environment variables

- `CLERK_PUBLISHABLE_KEY` = Clerk Development Publishable Key (`pk_test_...`)
- `CLERK_SECRET_KEY` = Clerk Development Secret Key (`sk_test_...`)

De Secret Key hoort uitsluitend in Netlify Environment Variables en **nooit** in GitHub of `index.html`.

## Synchronisatie

Na aanmelden haalt de app de centrale gegevens op. Als de centrale opslag nog leeg is, wordt de bestaande lokale Machinepark-data van het eerste toestel als startsnapshot opgeslagen. Elke wijziging wordt daarna automatisch naar Netlify Blobs geschreven. Andere geopende toestellen controleren periodiek op wijzigingen.

De browser bewaart nog steeds een lokale IndexedDB-cache zodat de bestaande appstructuur behouden blijft. De centrale Netlify-opslag is vanaf v1.23 de gedeelde bron tussen pc, iPhone en andere aangemelde toestellen.

Bij twee exact gelijktijdige wijzigingen op dezelfde centrale versie gebruikt de app ETag-controle om stil overschrijven te voorkomen; de nieuwere centrale versie wordt dan opnieuw geladen.
