# VNA-Craft

**VNA-Craft** is een Windows-desktopapplicatie voor het automatisch registreren van Q-waarden tijdens S21-metingen met een Copper Mountain Technologies TR1300/1 VNA.

## Huidige versie

**0.3.2 - Beta 3**

De huidige versie gebruikt de officiële TRVNA COM-automatiseringsinterface. De communicatie is getest met TRVNA 24.2.2 en een aangesloten TR1300/1.

## Functies

- Verbinding met `TRVNA.Application`.
- Selectie van channel, marker en triggerbron (`BUS` of `INT`).
- Eén BUS-trigger per meetpunt, gevolgd door uitlezen van markerdata.
- Registratie van Q, Qmax, bandwidth, center frequency en loss.
- Gemiddelde van de drie hoogste geldige Q-pieken.
- Live Q-grafiek; Q=0 wordt wel opgeslagen maar niet geplot.
- Meetduur, meetpuntenteller en frequentie bij Qmax.
- Automatische CSV- en Excel-opslag bij Stop.
- Coilnaam in de bestandsnaam.
- Optionele headless modus.
- Optionele Qratio-plugin voor unloaded/loaded metingen.
- Alle COM-aanroepen op één COM-workerthread.

## Installatie

1. Installeer Python 3.10 of nieuwer op Windows.
2. Start TRVNA en open de gewenste S21-meting.
3. Activeer in TRVNA de gewenste Marker Math / Bandwidth Search.
4. Voer `install.bat` uit.
5. Start `start_vna_craft_beta3.bat`.

## Gebruik

1. Kies channel, marker, interval en triggerbron.
2. Geef een coilnaam op.
3. Klik **Verbinden**.
4. Klik **Start registratie** en stop met **Stop**.
5. CSV en Excel worden automatisch opgeslagen in `metingen/`.

De applicatie verandert de span- of frequentie-instellingen van TRVNA niet. De bestaande instellingen in TRVNA blijven leidend.

## Qratio-plugin

De optionele plugin begeleidt unloaded en loaded metingen. De berekening is:

```text
Qratio = gemiddelde geldige Q unloaded / gemiddelde geldige Q loaded
```

Q=0 wordt niet meegenomen in de gemiddelden. Zie [`plugins/README_NL.md`](plugins/README_NL.md).

## Bestanden

- [`vna_craft_beta3.py`](vna_craft_beta3.py) - huidige applicatie.
- [`qratio_plugin.py`](qratio_plugin.py) - pluginmodule.
- [`requirements.txt`](requirements.txt) - Python-afhankelijkheden.
- [`CHANGELOG.md`](CHANGELOG.md) - formele wijzigingsgeschiedenis.
- [`VERSION`](VERSION) - huidige versie.
- [`archive/`](archive/) - oudere versies.
- [`plugins/`](plugins/) - optionele plugins en documentatie.

## Beperkingen

De hardwarecommunicatie vereist Windows, TRVNA 24.2.2 en een aangesloten TR1300/1. De applicatie doet geen eigen Q-berekening; Q wordt door TRVNA geleverd via Marker Math / Bandwidth Search.

Meetresultaten, CSV-bestanden en Excel-bestanden worden door `.gitignore` uitgesloten en worden niet naar GitHub geüpload.
