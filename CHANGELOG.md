# Changelog

Ce fichier suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
projet respecte [SemVer](https://semver.org/lang/fr/).

## [Unreleased]

### Added

- Modèle `Evenement` à clé stable, horaire ou journée entière.
- `Planificateur` : le plan de synchronisation (créer, modifier, supprimer) à
  partir de l'existant et de l'attendu, sans effet de bord.
- `ExportICS` : fichier iCalendar par-dessus `icalendar`, UID et URL dérivés de
  la clé.
- `Agenda` : écriture directe dans Calendar sous macOS par EventKit, événements
  reconnus par le champ URL `schema://cle`.
