"""L'événement à poser dans un agenda, et ce qu'une synchronisation en dit.

Un événement porte une **clé** stable, choisie par l'application appelante :
« seance/123 », « oral/2026-06-12/3 ». C'est elle qui permet, au passage
suivant, de retrouver l'événement pour le corriger ou le retirer. Sans clé on
ne sait que créer, et chaque passage fait des doublons : c'est le défaut des
exports iCalendar à UID aléatoire, et la raison d'être de ce paquet.

Deux formes coexistent, distinguées par le type des bornes : des `datetime`
pour un créneau horaire, des `date` pour une journée entière. Pour les dates,
la fin est **incluse** — « du 12 au 14 » se dit `fin=date(…, 14)` — parce que
c'est ainsi qu'on parle d'une période d'épreuves. Pour les instants, la fin est
exclue, comme partout.
"""

import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from zoneinfo import ZoneInfo

__all__ = [
    "FUSEAU_PAR_DEFAUT",
    "AccesRefuseError",
    "AgendaError",
    "Bilan",
    "Calendrier",
    "CalendrierIntrouvableError",
    "CleDupliqueeError",
    "CleInvalideError",
    "Evenement",
    "verifier_schema",
]

FUSEAU_PAR_DEFAUT = ZoneInfo("Europe/Paris")

# La clé voyage dans une URL (`schema://cle`) et dans un UID iCalendar : on la
# restreint aux caractères qui n'y demandent aucun échappement.
_MOTIF_CLE = re.compile(r"[A-Za-z0-9._~/-]+")
# Un schéma d'URI, au sens de la RFC 3986.
_MOTIF_SCHEMA = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*")


class AgendaError(Exception):
    """Erreur venue de l'agenda lui-même : accès, calendrier, enregistrement."""


class AccesRefuseError(AgendaError):
    """macOS n'a pas accordé l'accès au calendrier."""


class CalendrierIntrouvableError(AgendaError):
    """Aucun calendrier modifiable de ce nom, ou plusieurs."""


class CleInvalideError(ValueError):
    """La clé ou le schéma contient un caractère interdit."""


class CleDupliqueeError(ValueError):
    """Deux événements attendus portent la même clé."""


def verifier_schema(schema: str) -> str:
    """Rend le schéma s'il peut préfixer une URL, sinon lève `CleInvalideError`."""
    if not _MOTIF_SCHEMA.fullmatch(schema):
        raise CleInvalideError(f"schéma invalide : {schema!r} (lettres, chiffres, + . - seulement)")
    return schema


@dataclass(frozen=True, slots=True)
class Evenement:
    """Un événement tel que l'application le souhaite dans l'agenda."""

    cle: str
    titre: str
    debut: datetime | date
    fin: datetime | date
    lieu: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if not _MOTIF_CLE.fullmatch(self.cle):
            raise CleInvalideError(
                f"clé invalide : {self.cle!r} (lettres, chiffres, . _ ~ / - seulement)"
            )
        if not self.titre.strip():
            raise ValueError(f"titre vide pour la clé {self.cle!r}")
        if isinstance(self.debut, datetime) != isinstance(self.fin, datetime):
            raise ValueError(
                f"{self.cle!r} : début et fin doivent être deux instants ou deux dates"
            )
        if self.fin < self.debut:
            raise ValueError(f"{self.cle!r} : la fin précède le début")

    @property
    def journee_entiere(self) -> bool:
        # `datetime` est une sous-classe de `date` : c'est l'instant qu'on teste.
        return not isinstance(self.debut, datetime)

    @property
    def premier_jour(self) -> date:
        return self.debut.date() if isinstance(self.debut, datetime) else self.debut

    @property
    def dernier_jour(self) -> date:
        return self.fin.date() if isinstance(self.fin, datetime) else self.fin

    def en_fuseau(self, fuseau: ZoneInfo) -> "Evenement":
        """Le même événement, ses instants ancrés dans `fuseau` et arrondis à la seconde.

        Un instant naïf est lu dans ce fuseau ; un instant déjà situé y est
        converti. L'arrondi à la seconde évite qu'une relecture depuis l'agenda,
        qui ne conserve pas les microsecondes, ne passe pour une modification.
        """
        if not isinstance(self.debut, datetime) or not isinstance(self.fin, datetime):
            return self
        return replace(self, debut=_ancrer(self.debut, fuseau), fin=_ancrer(self.fin, fuseau))


def _ancrer(instant: datetime, fuseau: ZoneInfo) -> datetime:
    instant = instant.replace(microsecond=0)
    if instant.tzinfo is None:
        return instant.replace(tzinfo=fuseau)
    return instant.astimezone(fuseau)


@dataclass(frozen=True, slots=True)
class Calendrier:
    """Un calendrier tel que l'agenda le présente."""

    nom: str
    source: str
    modifiable: bool


@dataclass(frozen=True, slots=True)
class Bilan:
    """Ce qu'une synchronisation a fait, clé par clé."""

    crees: tuple[str, ...] = ()
    modifies: tuple[str, ...] = ()
    supprimes: tuple[str, ...] = ()
    inchanges: tuple[str, ...] = ()

    def __str__(self) -> str:
        return ", ".join(
            (
                _compter(len(self.crees), "créé"),
                _compter(len(self.modifies), "modifié"),
                _compter(len(self.supprimes), "supprimé"),
                _compter(len(self.inchanges), "inchangé"),
            )
        )


def _compter(n: int, mot: str) -> str:
    return f"{n} {mot}{'s' if n > 1 else ''}"
