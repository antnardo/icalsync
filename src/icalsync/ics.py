"""Export iCalendar à clés stables, par-dessus `icalendar`.

Le fichier reste utile là où EventKit ne va pas : un import unique dans
n'importe quel agenda, un envoi à quelqu'un d'autre, une machine sans macOS.
Chaque événement y porte un UID dérivé de sa clé, et la même URL `schema://cle`
que l'écriture EventKit : un fichier importé à la main dans Calendar est ensuite
reconnu, et repris, par `Agenda.synchroniser`.

Pas de règle de répétition : un événement par occurrence. C'est plus long, mais
c'est la seule forme où déplacer une séance ne casse rien.
"""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from icalsync.modeles import FUSEAU_PAR_DEFAUT, Evenement, verifier_schema
from icalsync.plan import indexer

__all__ = ["ExportICS"]


class ExportICS:
    """Compose un calendrier iCalendar à partir d'événements à clé."""

    def __init__(
        self,
        schema: str,
        fuseau: ZoneInfo = FUSEAU_PAR_DEFAUT,
        nom_calendrier: str = "",
        prodid: str = "-//antnardo//icalsync//FR",
    ) -> None:
        self._schema = verifier_schema(schema)
        self._fuseau = fuseau
        self._nom = nom_calendrier
        self._prodid = prodid

    def composer(self, evenements: Iterable[Evenement]) -> bytes:
        """Le texte iCalendar, encodé comme la RFC 5545 l'exige (CRLF, UTF-8)."""
        calendrier = Calendar()
        calendrier.add("prodid", self._prodid)
        calendrier.add("version", "2.0")
        calendrier.add("calscale", "GREGORIAN")
        calendrier.add("method", "PUBLISH")
        if self._nom:
            calendrier.add("x-wr-calname", self._nom)
        horodatage = datetime.now(UTC).replace(microsecond=0)
        for evenement in indexer(evenements).values():
            calendrier.add_component(self._composant(evenement, horodatage))
        # Les VTIMEZONE que Calendar attend pour les instants à TZID.
        calendrier.add_missing_timezones()
        return bytes(calendrier.to_ical())

    def ecrire(self, evenements: Iterable[Evenement], fichier: Path) -> bytes:
        contenu = self.composer(evenements)
        fichier.write_bytes(contenu)
        return contenu

    def _composant(self, evenement: Evenement, horodatage: datetime) -> Event:
        situe = evenement.en_fuseau(self._fuseau)
        composant = Event()
        composant.add("uid", f"{situe.cle}@{self._schema}")
        composant.add("url", f"{self._schema}://{situe.cle}")
        composant.add("summary", situe.titre)
        composant.add("dtstamp", horodatage)
        if situe.journee_entiere:
            composant.add("dtstart", situe.debut)
            # DTEND exclusif dans la norme, alors que notre fin est incluse.
            composant.add("dtend", situe.fin + timedelta(days=1))
        else:
            composant.add("dtstart", situe.debut)
            composant.add("dtend", situe.fin)
        if situe.lieu:
            composant.add("location", situe.lieu)
        if situe.notes:
            composant.add("description", situe.notes)
        return composant
