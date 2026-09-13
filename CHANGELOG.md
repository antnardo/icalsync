# Journal des modifications

Le format suit [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/) et le
versionnage sémantique. Chaque version est un tag `v<version>` et une release
GitHub, à laquelle la distribution est jointe ; rien n'est publié sur PyPI.

## [Non publié]

### Corrigé

- Les journées entières passaient par le fuseau de l'appelant alors que
  Calendar les range dans celui du système : sur une machine hors
  Europe/Paris, elles reculaient d'un jour. Vu en CI, sur les exécuteurs en UTC.

## [0.1.0] — 2026-09-13

### Ajouté

- Modèle `Evenement` à clé stable, horaire ou journée entière.
- `Planificateur` : le plan de synchronisation (créer, modifier, supprimer) à
  partir de l'existant et de l'attendu, sans effet de bord.
- `ExportICS` : fichier iCalendar par-dessus `icalendar`, UID et URL dérivés de
  la clé.
- `Agenda` : écriture directe dans Calendar sous macOS par EventKit, événements
  reconnus par le champ URL `schema://cle`.

[Non publié]: https://github.com/antnardo/icalsync/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/antnardo/icalsync/releases/tag/v0.1.0
