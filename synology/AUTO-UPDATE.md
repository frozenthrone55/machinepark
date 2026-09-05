# Automatische updates van GitHub naar Synology

De aanbevolen stroom is:

```
synology-selfhost
      ↓ push
GitHub Actions bouwt Machinepark
      ↓
synology-deploy
      ↓ elke 10 minuten
DS1813+ Taakplanner
      ↓
/volume1/web/machinepark
```

De lokale gegevens staan apart in:

```
/volume1/MachineparkData
```

en worden door de updater nooit vervangen.

## Eenmalige installatie op de NAS

1. Kopieer `synology/update-from-github.sh` naar bijvoorbeeld:

```
/volume1/MachineparkData/update-from-github.sh
```

2. Maak het uitvoerbaar. Dit kan via SSH:

```sh
chmod +x /volume1/MachineparkData/update-from-github.sh
```

Als je liever geen SSH gebruikt, kan het script ook rechtstreeks vanuit DSM Taakplanner met `/bin/sh` worden gestart.

3. Open **DSM → Configuratiescherm → Taakplanner**.

4. Kies **Maken → Geplande taak → Door gebruiker gedefinieerd script**.

5. Gebruik voor de eerste test als gebruiker **root** en voer uit:

```sh
/bin/sh /volume1/MachineparkData/update-from-github.sh
```

6. Laat de taak bijvoorbeeld iedere 10 minuten draaien.

## Wat gebeurt er bij een wijziging?

Wanneer er iets in `synology-selfhost` verandert:

- GitHub bouwt eerst de volledige app;
- alleen de bestanden die de browser/NAS werkelijk nodig heeft komen in `synology-deploy`;
- de NAS ziet een nieuwe `source_sha`;
- de huidige webapp wordt één keer geback-upt naar
  `/volume1/MachineparkData/backups/machinepark-web-last-good.tar.gz`;
- de nieuwe programmabestanden worden naar
  `/volume1/web/machinepark` gekopieerd;
- data, foto's, handleidingen en uploads onder
  `/volume1/MachineparkData` blijven onaangeroerd.

## Logboek

De updater schrijft naar:

```
/volume1/MachineparkData/backups/synology-update.log
```

## Huidige online app

Deze automatische route gebruikt uitsluitend de branches
`synology-selfhost` en `synology-deploy`.
De huidige `development`/Netlify-versie wordt hierdoor niet gewijzigd.
