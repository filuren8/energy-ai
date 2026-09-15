# Energy AI V0.1

Windows-prototyp för live-data från Ferroamp EnergyHub via External API/MQTT och ett simulerat villabatteri.

## V0.1
- EnergyHub: `192.168.68.59`
- MQTT topic: `extapi/data/ehub`
- 15 kWh virtuellt batteri, 5 kW max
- SOC 10–95 %, start 50 %, 95 % verkningsgrad
- Peak shaving: 10 kW
- Ingen styrning skickas till Ferroamp i V0.1
- Lokal dashboard: http://localhost:8000

## Kör som Windows-EXE (ingen Python behövs)
GitHub Actions bygger automatiskt `EnergyAI.exe` på en Windows-runner. Hämta senaste development release från repo-sidan under Releases, packa vid behov upp artifacten och kör `EnergyAI.exe`.

Vid första testet behöver programmet fortfarande en lokal `.env` i samma arbetsmapp med:
```
FERROAMP_HOST=192.168.68.59
FERROAMP_PORT=1883
FERROAMP_USERNAME=ditt_anvandarnamn
FERROAMP_PASSWORD=ditt_losenord
```
Datorn måste vara på samma LAN som EnergyHub. Credentials ska aldrig committas till GitHub.

## Bygg själv
Om du vill bygga EXE lokalt kan du köra `build_exe.bat`. Python krävs endast på datorn som bygger programmet, inte på datorn som kör den färdiga EXE-filen.

## Säkerhet
`.env` ignoreras av Git. V0.1 prenumererar endast på mätdata och publicerar inga styrkommandon till EnergyHub.

## Nästa steg
Verifiera tecken/riktning för `pload` och `pext` på den verkliga installationen. Därefter: SE2-priser, historik, lastprognos, 24h-optimerare, self-use och prisstyrning.
