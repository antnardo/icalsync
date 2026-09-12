"""Le plan d'une synchronisation : ce qu'il faut faire, séparé de la façon de le faire.

Confronter l'existant à l'attendu ne dépend pas de l'agenda visé. Sorti d'ici,
le calcul se teste sans macOS ni fichier, et les deux sorties — EventKit et
iCalendar — n'ont plus qu'à l'exécuter.

Un événement existant dont la clé n'est plus attendue est un **orphelin** : une
séance supprimée dans l'application. Le retirer est le comportement voulu, et
le seul qui tienne l'agenda égal à l'application ; on peut le désactiver pour
un premier passage prudent.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from icalsync.modeles import CleDupliqueeError, Evenement

__all__ = ["Plan", "Planificateur", "bornes", "indexer"]


@dataclass(frozen=True, slots=True)
class Plan:
    """Les trois listes d'actions, plus ce qui n'a pas bougé."""

    a_creer: tuple[Evenement, ...] = ()
    a_modifier: tuple[Evenement, ...] = ()
    a_supprimer: tuple[str, ...] = ()
    inchanges: tuple[str, ...] = ()

    @property
    def vide(self) -> bool:
        return not (self.a_creer or self.a_modifier or self.a_supprimer)


def indexer(evenements: Iterable[Evenement]) -> dict[str, Evenement]:
    """Les événements par clé ; deux clés égales sont une erreur de l'appelant."""
    index: dict[str, Evenement] = {}
    for evenement in evenements:
        if evenement.cle in index:
            raise CleDupliqueeError(f"clé en double : {evenement.cle!r}")
        index[evenement.cle] = evenement
    return index


def bornes(evenements: Sequence[Evenement]) -> tuple[date, date]:
    """Le premier et le dernier jour couverts, inclus."""
    if not evenements:
        raise ValueError("aucun événement : pas de bornes")
    return (
        min(evenement.premier_jour for evenement in evenements),
        max(evenement.dernier_jour for evenement in evenements),
    )


class Planificateur:
    """Tire le plan d'une confrontation entre l'existant et l'attendu."""

    def __init__(self, supprimer_orphelins: bool = True) -> None:
        self._supprimer_orphelins = supprimer_orphelins

    def etablir(self, existants: Mapping[str, Evenement], souhaites: Iterable[Evenement]) -> Plan:
        """Compare champ à champ : les deux côtés doivent être dans le même fuseau."""
        attendus = indexer(souhaites)
        a_creer: list[Evenement] = []
        a_modifier: list[Evenement] = []
        inchanges: list[str] = []
        for cle, evenement in attendus.items():
            existant = existants.get(cle)
            if existant is None:
                a_creer.append(evenement)
            elif existant == evenement:
                inchanges.append(cle)
            else:
                a_modifier.append(evenement)
        orphelins = [cle for cle in existants if cle not in attendus]
        return Plan(
            a_creer=tuple(a_creer),
            a_modifier=tuple(a_modifier),
            a_supprimer=tuple(orphelins) if self._supprimer_orphelins else (),
            inchanges=tuple(inchanges),
        )
