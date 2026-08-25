# Machinepark v1.22 — Development

Machinepark is de webapp voor toestellen, onderhoud, depannages en onderdelen.
Deze Development-versie gebruikt GitHub voor de broncode, Netlify voor hosting en Clerk voor aanmelden.

## GitHub
Repository: `machinepark`

Netlify wordt straks rechtstreeks gekoppeld aan deze GitHub-repository. Nieuwe commits op `main` kunnen daardoor automatisch opnieuw worden gedeployed.

## Clerk Development
1. Maak/open in Clerk de application **Machinepark**.
2. Blijf voorlopig in **Development**.
3. Kopieer bij **API Keys** de Publishable Key die begint met `pk_test_`.
4. Zet nooit een Clerk Secret Key (`sk_test_...`) in GitHub.

## Netlify Development
1. Kies **Add new project → Import an existing project → GitHub**.
2. Selecteer repository `machinepark`.
3. Gebruik `main` als production branch.
4. Voeg bij Environment variables toe:
   - Key: `CLERK_PUBLISHABLE_KEY`
   - Value: jouw Clerk Development Publishable Key (`pk_test_...`)
5. Deploy de site.

## iPhone
Open altijd het Netlify HTTPS-adres in Safari of Chrome. Open `index.html` niet rechtstreeks vanuit de Bestanden-app.

## Gegevens
Clerk verzorgt in v1.22 alleen de gebruikerslogin. De Machinepark-gegevens worden nog lokaal in IndexedDB van de browser bewaard. Daardoor delen pc en iPhone de gegevens nog niet automatisch.

Voor centrale gedeelde data is later een centrale database/API nodig met Clerk-authenticatie.
