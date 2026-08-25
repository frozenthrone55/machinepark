# Machinepark DEVELOPMENT — zero Netlify credits

Deze branch is bedoeld voor veilig testen zonder production deploys.

## Lokaal testen zonder Netlify cloud-usage
1. Installeer Node.js LTS.
2. Clone/download deze `development` branch.
3. Kopieer `.env.example` naar `.env` en vul alleen Clerk Development keys in (`pk_test_...` en `sk_test_...`).
4. Start `start-development.bat`.
5. Open `http://127.0.0.1:8888`.

De developmentversie gebruikt een kleine lokale Node-server. De routes `/.netlify/functions/...` worden lokaal nagebootst en de testdata wordt opgeslagen in `.dev-data/machinepark-state.json`. Tijdens deze lokale test worden dus geen Netlify production deploys, Netlify Functions of Netlify Blobs in de cloud gebruikt.

## Opnieuw schoon beginnen
Stop de server en verwijder de map `.dev-data`. Start daarna opnieuw.

## Online development
Een Netlify Deploy Preview/branch deploy kost 0 deploy-credits, maar requests, bandbreedte en function compute kunnen nog wel metered usage geven. Gebruik daarom de lokale testmodus als je Netlify-credits helemaal niet wilt laten dalen.

## Belangrijk
- Commit `.env` nooit naar GitHub.
- Gebruik hier nooit `pk_live_...` of `sk_live_...`.
- Merge pas naar `main` wanneer de test geslaagd is.
