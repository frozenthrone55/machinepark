# Machinepark DEVELOPMENT

Deze branch is bedoeld voor veilig testen zonder production deploys.

## Aanbevolen: lokaal testen zonder Netlify cloud-usage
1. Installeer Node.js LTS.
2. Clone/download deze `development` branch.
3. Kopieer `.env.example` naar `.env` en vul alleen Clerk Development keys in (`pk_test_...` en `sk_test_...`).
4. Start `start-development.bat`.
5. Open `http://localhost:8888`.

Netlify Dev draait Functions lokaal en Netlify Blobs gebruikt een lokale sandbox. De development functie gebruikt bovendien de aparte store `machinepark-development`.

## Online development
Een Netlify Deploy Preview/branch deploy kost 0 deploy-credits, maar requests, bandbreedte en function compute kunnen nog wel metered usage geven. Gebruik lokaal testen als je Netlify-credits helemaal niet wilt laten dalen.

## Belangrijk
- Commit `.env` nooit naar GitHub.
- Gebruik hier nooit `pk_live_...` of `sk_live_...`.
- Merge pas naar `main` wanneer de test geslaagd is.
