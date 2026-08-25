# KoffieService Pro v1.22 — Netlify + Clerk

Deze versie is bedoeld om via Netlify te hosten en gebruikt Clerk voor aanmelden.

## 1. Clerk
1. Maak/open je Clerk application.
2. Kopieer in Clerk Dashboard → API Keys de **Publishable Key** (`pk_test_...` of later `pk_live_...`).
3. Voor een eerste test op een `*.netlify.app`-adres gebruik je best de Development key (`pk_test_...`).
4. Voor Clerk Production (`pk_live_...`) gebruik je een eigen domein dat in Clerk als productiedomein is ingesteld.

## 2. Netlify
1. Log in op Netlify.
2. Maak een site/project en upload deze volledige map/ZIP (Netlify Drop is voldoende).
3. Ga in het Netlify-project naar **Project configuration → Environment variables**.
4. Voeg toe:
   - Key: `CLERK_PUBLISHABLE_KEY`
   - Value: jouw Clerk Publishable Key
5. Deploy/redeploy de site.
6. Open het `https://...netlify.app`-adres in Chrome of Safari op iPhone.

## 3. iPhone
Open altijd het Netlify HTTPS-adres, niet `index.html` vanuit de Bestanden-app. Je kunt de site via Safari ook aan het beginscherm toevoegen.

## Belangrijk over gegevens
Clerk verzorgt in v1.22 de gebruikerslogin. De KoffieService-gegevens zelf worden nog lokaal in IndexedDB van de browser bewaard. Daardoor deelt een iPhone niet automatisch dezelfde wijzigingen met een andere pc of telefoon. Gebruik Beheer → Back-up voor overdracht/herstel.

Voor centrale gedeelde data is een volgende stap nodig: een Netlify API + centrale database/storage, waarbij de Clerk-sessie server-side wordt gecontroleerd.
