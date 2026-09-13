# icalsync

Des événements à **clé stable**, posés dans un agenda et tenus à jour au passage
suivant : créés s'ils manquent, corrigés s'ils ont bougé, retirés s'ils n'ont
plus lieu d'être. Deux sorties pour un même modèle :

- `Agenda` écrit directement dans Calendar sous macOS, par EventKit, donc dans
  iCloud sans mot de passe d'application ;
- `ExportICS` produit un fichier iCalendar, pour un import unique ailleurs.

Dans les deux cas l'événement porte `schema://cle` dans son champ URL. C'est ce
marqueur, et non un UID tiré au hasard, qui permet de le retrouver.

## Le problème

Une application qui tient un emploi du temps — un cahier de texte, un planning
d'oraux — veut le voir dans l'agenda du téléphone. Le réflexe est d'exporter un
fichier `.ics` et de l'importer dans Calendar. Ça marche une fois. À la seconde
modification, le fichier réimporté crée un doublon de chaque événement, parce
que ses UID sont tirés au sort à chaque export et que rien ne relie la nouvelle
version à l'ancienne. On finit par supprimer tout le calendrier et réimporter,
ou par ne plus exporter.

Ce qu'il faut, c'est que l'application puisse dire « voici les événements tels
qu'ils doivent être » et que l'agenda s'y conforme : c'est une réconciliation,
pas un import. icalsync fait cette réconciliation, et rien d'autre.

## Ce que fait icalsync

- `Evenement` : une clé choisie par l'application (`seance/123`), un titre, un
  début et une fin, un lieu, des notes. Deux `datetime` pour un créneau, deux
  `date` pour une journée entière.
- `Planificateur` : confronte l'existant à l'attendu et rend un plan — à créer,
  à modifier, à supprimer, inchangés — sans toucher à rien. Il se teste seul.
- `ExportICS` : le plan appliqué à un fichier, par-dessus `icalendar`. UID
  `cle@schema`, URL `schema://cle`, fuseau et `VTIMEZONE` gérés.
- `Agenda` : le plan appliqué à Calendar, par pyobjc et EventKit. Les
  événements sont retrouvés par leur URL dans une fenêtre de dates, et tout
  s'enregistre en une seule validation.

Un fichier écrit par `ExportICS` puis importé à la main dans Calendar est
ensuite reconnu par `Agenda.synchroniser` : les deux sorties parlent la même
langue.

## Installation

```bash
pip install icalsync            # export iCalendar seulement
pip install "icalsync[mac]"     # plus l'écriture dans Calendar (macOS)
```

## Usage

```python
from datetime import datetime
from pathlib import Path

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
la fenêtre de dates la couvre : passer `debut` et `fin` pour l'élargir. Le
script `examples/aller_retour.py` joue le cycle complet — création, relecture,
déplacement, retrait — dans un calendrier réel, et nettoie derrière lui.

## Comparaison avec l'existant

Recherche d'antériorité du 12 septembre 2026. Quatre façons d'amener des
événements dans un agenda existaient déjà ; aucune ne faisait la réconciliation
par clé, qui est la seule chose qu'icalsync ajoute.

### Les quatre approches

1. **Le fichier importé à la main.** Une bibliothèque sérialise, l'utilisateur
   importe. Simple et portable, mais l'import ne sait pas mettre à jour :
   chaque passage double.
2. **L'accès direct à Calendar.** EventKit, ou AppleScript, écrit dans le
   magasin de Calendar, qui remonte vers iCloud. Aucun secret à ranger, mais
   macOS seulement, et une autorisation à obtenir.
3. **CalDAV.** Le protocole des serveurs d'agenda, iCloud compris. Marche
   depuis n'importe quelle machine, au prix d'un mot de passe d'application à
   conserver et d'une prise en charge d'iCloud « partielle » de l'aveu même des
   bibliothèques.
4. **L'API web privée d'iCloud.** Ce que fait le site icloud.com, rejoué en
   Python. Non documentée, fragile à la double authentification, cassée à
   chaque changement côté Apple.

Une cinquième, l'abonnement `webcal`, est un cas du fichier : Calendar le
rafraîchit lui-même, à condition d'héberger le fichier sur une URL publique, et
l'agenda devient en lecture seule.

### Projet par projet

| Projet | Nature | Chemin vers l'agenda | Réconciliation par clé | Répétition | Plateforme |
| --- | --- | --- | --- | --- | --- |
| icalsync | bibliothèque | EventKit, ou fichier `.ics` | oui, URL `schema://cle` | non, une occurrence par événement | macOS pour `Agenda`, partout pour `ExportICS` |
| [icalendar](https://github.com/collective/icalendar) | bibliothèque | fichier | non, sérialisation seulement | oui | partout |
| [ics](https://github.com/ics-py/ics-py) | bibliothèque | fichier | non | oui | partout |
| [maccal](https://github.com/appenz/maccal) | bibliothèque | EventKit | non, création, recherche, modification, suppression | occurrences dépliées | macOS |
| [apple-pim](https://github.com/omarshahine/apple-pim), [ekctl](https://github.com/schappim/ekctl) | outils Swift et Node | EventKit | non | oui | macOS |
| AppleScript via `osascript` | script | Calendar.app | non | oui | macOS, lent |
| [caldav](https://github.com/python-caldav/caldav) | bibliothèque | CalDAV | par UID, `save_event` écrase | oui | partout |
| [calendar-sync](https://github.com/magicdude4eva/calendar-sync) | outil en ligne de commande | CalDAV | UID déterministes calculés du flux | dépliée en occurrences | partout |
| [vdirsyncer](https://github.com/pimutils/vdirsyncer) | outil en ligne de commande | CalDAV vers fichiers, et retour | par UID, dans les deux sens | oui | partout |
| [pyicloud](https://github.com/picklepete/pyicloud) | bibliothèque | API web privée d'iCloud | par `guid` | oui | partout, fragile |
| [apple-calendar-integration](https://pypi.org/project/apple-calendar-integration/) | bibliothèque | API web privée d'iCloud | par `guid` | oui | abandonnée, 0.0.1 de 2018 |

### Où icalsync se place

- **Par rapport à `icalendar` et `ics`** : icalsync ne sérialise pas, il
  s'appuie sur `icalendar` pour ça. Il ajoute la clé, l'URL marqueur et le
  plan.
- **Par rapport à `maccal`** : même couche d'accès à EventKit, en plus court et
  sans autre dépendance que pyobjc ; `maccal` n'a pas de notion d'ensemble
  attendu, il expose des opérations une à une. Ce sont deux cents lignes
  d'`eventkit.py` que `maccal` aurait pu remplacer, contre une dépendance à un
  projet jeune, à un seul auteur.
- **Par rapport à `caldav`** : c'est le socle qu'une sortie CalDAV d'icalsync
  utiliserait, si elle venait. `Planificateur` ne dépend pas de la sortie ;
  seule la couche d'accès changerait. Tant que l'application tourne sur le Mac
  où Calendar est ouvert, EventKit fait le même travail sans secret.
- **Par rapport à `calendar-sync`** : l'idée la plus proche — des UID
  déterministes pour reconnaître les événements d'un passage à l'autre, des
  répétitions dépliées en occurrences — mais sous forme d'outil qui consomme des
  flux `.ics`, quand icalsync est une bibliothèque qu'une application appelle
  avec ses propres objets.
- **Par rapport à `vdirsyncer`** : une synchronisation bidirectionnelle entre
  un serveur et des fichiers locaux, faite pour un client en ligne de commande
  comme `khal`. Ce n'est pas le problème d'une application qui veut pousser son
  état.

### Pourquoi pas de répétition

Une règle hebdomadaire plus des exceptions est une compression d'une liste
d'occurrences, à recalculer à chaque passage. Une fois dans Calendar, modifier
une occurrence la détache de la série, et le passage suivant doit reconnaître
ce qui a bougé entre la série, les détachées et les supprimées. La solution
simple — détruire et recréer la série à la moindre différence — efface les
alarmes posées à la main et fait défiler des notifications sur tous les
appareils. Une occurrence par événement, c'est trois cents objets au lieu de
quinze, ce qui ne change rien à l'échelle d'iCloud, et c'est la seule forme où
déplacer une séance ne casse rien. `calendar-sync` a fait le même choix.

## L'autorisation macOS

L'accès au calendrier est accordé à l'application **responsable** du processus.
Lancé depuis Terminal, le script déclenche la fenêtre « Terminal souhaite
accéder à votre calendrier » ; lancé depuis une application qui ne déclare pas
cet usage (VS Code, un agent), il est refusé sans fenêtre et `Agenda.ouvrir`
lève `AccesRefuseError`. En cas de doute : relancer depuis Terminal.app.

## Limites

- Pas de règle de répétition, par choix, voir plus haut.
- `Agenda` ne tourne que sous macOS ; `ExportICS` tourne partout.
- Une fenêtre EventKit ne dépasse pas quatre ans.
- Les événements sans marqueur URL, importés avant icalsync, ne sont jamais
  touchés : les retirer une fois à la main avant la première synchronisation.

## Développement

```bash
uv sync --group dev
uv run ruff format src tests examples
uv run ruff check src tests examples
uv run mypy
uv run pytest -q
```

Les tests d'`eventkit.py` qui ne touchent pas au magasin tournent partout où
pyobjc est installé ; ceux qui écrivent dans un vrai calendrier ne sont pas des
tests, c'est `examples/aller_retour.py`.
