VNA-Craft Beta 3

Beta 3 is een visuele verbetering van Beta 1. De bestaande functies,
meetlogica, VNA-koppeling, automatische opslag en knoppen zijn behouden.
Er zijn geen nieuwe bedieningselementen of niet-functionele schermen
toegevoegd.

Visuele verbeteringen:
- betere leesbaarheid op kleine en halve schermen;
- responsief meetwaardenblok;
- professionele donkere kleurstelling;
- duidelijkere panelen, randen, marges en knopstatussen;
- ruimere standaardafmetingen met behoud van verkleinen.

Start met start_vna_craft_beta3.bat.

Beta 2 wordt niet als geslaagde versie beschouwd.

Optionele Qratio-plugin
Klik op `Start Qratio` om een begeleide tweefasenmeting te starten:
1. plaats de unloaded coil en klik `Start registratie`;
2. klik `Stop`; de unloaded fase wordt opgeslagen en de plugin wacht op loaded;
3. plaats de loaded coil, klik `Start registratie` en daarna `Stop`.

De plugin berekent:
`Qratio = gemiddelde geldige Q unloaded / gemiddelde geldige Q loaded`.
Q=0 wordt niet meegenomen in deze gemiddelden. De gebruiker bepaalt zelf
wanneer elke fase start, stopt of opnieuw wordt gestart.
