# icalsync — documentation

## Le modèle

`Evenement(cle, titre, debut, fin, lieu="", notes="")`, figé.

- `cle` : identifiant stable dans l'application appelante, restreint à
  `A-Z a-z 0-9 . _ ~ / -` pour tenir dans une URL et un UID sans échappement.
- `debut`, `fin` : deux `datetime` pour un créneau (fin exclue), deux `date`
  pour une journée entière (fin **incluse**).
- `en_fuseau(fuseau)` ancre les instants naïfs et arrondit à la seconde, pour
  que la comparaison avec ce que l'agenda relit soit fiable.

## Le plan

`Planificateur(supprimer_orphelins=True).etablir(existants, souhaites)` rend un
`Plan` : `a_creer`, `a_modifier`, `a_supprimer` (clés), `inchanges` (clés). Les
deux côtés doivent être dans le même fuseau ; c'est `Agenda` qui s'en charge.

## Calendar (macOS)

```python
agenda = Agenda.ouvrir(fuseau=ZoneInfo("Europe/Paris"), delai=120)
agenda.calendriers()                          # list[Calendrier(nom, source, modifiable)]
agenda.lire(calendrier, schema, debut, fin)   # list[Evenement]
agenda.synchroniser(calendrier, evenements, schema, debut=None, fin=None,
                    supprimer_orphelins=True)  # Bilan
agenda.purger(calendrier, schema, debut, fin) # int
```

La fenêtre de `synchroniser` est celle des événements attendus, élargie à
`debut` et `fin` s'ils sont donnés. Ce qui la déborde n'est ni lu ni touché.
Deux événements portant la même clé dans la fenêtre — un import répété — sont
ramenés à un seul.

Toutes les écritures d'un appel sont validées en une fois (`commit`) : Calendar
ne voit rien tant que l'appel n'est pas au bout.

Une journée entière est un jour flottant : Calendar la range dans le fuseau du
système, et `fuseau` n'y intervient pas. Un créneau, lui, est un instant, et
`fuseau` ne sert qu'à lire les `datetime` naïfs.

## iCalendar

`ExportICS(schema, fuseau=…, nom_calendrier="", prodid=…)` avec `composer()` qui
rend les octets et `ecrire()` qui les pose dans un fichier. UID `cle@schema`,
URL `schema://cle` : un fichier importé à la main dans Calendar est ensuite
reconnu par `Agenda.synchroniser`.

## Pourquoi pas CalDAV

CalDAV donnerait le même résultat depuis n'importe quelle machine, au prix d'un
mot de passe d'application iCloud à conserver. Tant que l'application tourne sur
le Mac où Calendar est ouvert, EventKit fait le même travail sans secret. Une
sortie CalDAV pourrait s'ajouter derrière la même interface, `Planificateur`
étant indépendant de la sortie.
