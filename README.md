# icalsync

Des événements à **clé stable**, posés dans un agenda et tenus à jour au passage
suivant : créés s'ils manquent, corrigés s'ils ont bougé, retirés s'ils n'ont
plus lieu d'être. Deux sorties pour un même modèle :

- `Agenda` écrit directement dans Calendar sous macOS, par EventKit, donc dans
  iCloud sans mot de passe d'application ;
- `ExportICS` produit un fichier iCalendar, pour un import unique ailleurs.

Dans les deux cas l'événement porte `schema://cle` dans son champ URL. C'est ce
marqueur, et non un UID tiré au hasard, qui permet de le retrouver.

## Installation

```bash
pip install icalsync            # export iCalendar seulement
pip install "icalsync[mac]"     # plus l'écriture dans Calendar (macOS)
```

## Usage

```python
from datetime import datetime
from icalsync import Agenda, Evenement, ExportICS

seances = [
    Evenement("seance/12", "Cours", datetime(2026, 9, 14, 8), datetime(2026, 9, 14, 10),
              lieu="Salle 12", notes="Chapitre 3"),
]

agenda = Agenda.ouvrir()                                   # demande l'accès, une fois
bilan = agenda.synchroniser("Cours", seances, schema="cahiertexte")
print(bilan)                                               # 1 créé, 0 modifié, 0 supprimé, 0 inchangé

ExportICS(schema="cahiertexte").ecrire(seances, Path("export/cours.ics"))
```

Une séance retirée de `seances` disparaît du calendrier au passage suivant, si
la fenêtre de dates la couvre : passer `debut` et `fin` pour l'élargir.

## L'autorisation macOS

L'accès au calendrier est accordé à l'application **responsable** du processus.
Lancé depuis Terminal, le script déclenche la fenêtre « Terminal souhaite
accéder à votre calendrier » ; lancé depuis une application qui ne déclare pas
cet usage (VS Code, un agent), il est refusé sans fenêtre et `Agenda.ouvrir`
lève `AccesRefuseError`. En cas de doute : relancer depuis Terminal.app.

## Projets voisins

Recherche d'antériorité du 12 septembre 2026. Les briques existent, la
réconciliation par clé au-dessus d'elles non.

- [maccal](https://github.com/appenz/maccal) : accès EventKit depuis Python,
  création, recherche, modification, suppression. Pas de synchronisation d'un
  ensemble attendu ; c'est la couche que `Agenda` réécrit, en plus court.
- [caldav](https://github.com/python-caldav/caldav) : client CalDAV, avec
  `save_event` qui écrase par UID. La sortie CalDAV d'icalsync, si elle vient,
  s'écrira dessus.
- [calendar-sync](https://github.com/magicdude4eva/calendar-sync) : outil en
  ligne de commande qui verse des flux ICS dans un CalDAV avec des UID
  déterministes et déplie les répétitions en occurrences. Même idée, sous forme
  d'outil et non de bibliothèque, et sans EventKit.
- [icalendar](https://github.com/collective/icalendar) : la sérialisation,
  dont `ExportICS` dépend.

## Limites

- Pas de règle de répétition : un événement par occurrence, ce qui est aussi la
  seule forme où déplacer une occurrence ne casse rien.
- `Agenda` ne tourne que sous macOS ; `ExportICS` tourne partout.
- Une fenêtre EventKit ne dépasse pas quatre ans.
