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

## Windows
1. Installera Python 3.11+.
2. Ladda ned/klona repot.
3. Dubbelklicka `run.bat`.
4. Första körningen skapar `.env`. Stäng programmet.
5. Öppna `.env` och fyll i `FERROAMP_USERNAME` och `FERROAMP_PASSWORD`.
6. Kör `run.bat` igen.
7. Dashboarden öppnas på localhost.

Datorn måste vara på samma LAN som EnergyHub.

## Säkerhet
Credentials ligger endast i lokal `.env`, som ignoreras av Git. V0.1 prenumererar endast på mätdata och publicerar inga styrkommandon till EnergyHub.

## Nästa steg
Verifiera tecken/riktning för `pload` och `pext` på den verkliga installationen. Därefter: SE2-priser, historik, lastprognos, 24h-optimerare, self-use och prisstyrning.
