# Changelog

Alle wijzigingen worden formeel en chronologisch vastgelegd. Versies volgen Semantic Versioning: `MAJOR.MINOR.PATCH`.

## [0.3.2] - 2026-11-16

### Documentation

- Professionele repository-README toegevoegd met functies, installatie en gebruik.
- Oudere releases ondergebracht in `archive/`.
- Plugin-documentatie toegevoegd onder `plugins/`.
- Repositorystructuur verduidelijkt voor collega-gebruikers.

## [0.3.1] - 2026-11-16

### Added

- Een repositorybrede `.gitignore` toegevoegd.
- Meetresultaten in `metingen/`, CSV-bestanden en Excel-bestanden worden niet meer door Git gevolgd en kunnen dus niet per ongeluk worden geüpload.
- Lokale Python-cachebestanden en editorconfiguratie uitgesloten.
- Versiebeheer toegevoegd via `VERSION`.

### Documentation

- Changelog toegevoegd voor formele registratie van wijzigingen.

## [0.3.0] - 2026-11-16

### Added

- Optionele Qratio-workflow voor unloaded en loaded metingen.
- Gemiddelde Q-berekening per fase en verhouding `Qratio = unloaded / loaded`.

### Changed

- VNA-Craft Beta 3 benoemd als visuele voortzetting van Beta 1.

## [0.2.0] - 2026-11-16

### Added

- VNA-Craft Beta 3 visuele interfaceverbeteringen.
- Automatische opslag van metingen op basis van coilnaam.
- BUS/INT-triggerkeuze.

## [0.1.0] - 2026-11-16

### Added

- Eerste VNA-Craft Beta 1 met TRVNA COM-communicatie.
- Qmax-registratie, live grafiek en CSV/Excel-export.
