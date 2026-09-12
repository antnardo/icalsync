"""Écriture directe dans Calendar sous macOS, par EventKit.

Pourquoi EventKit plutôt que CalDAV : l'agenda visé est celui d'iCloud, et
Calendar l'a déjà ouvert sur ce Mac. Passer par lui évite de ranger un mot de
passe d'application, et la remontée vers iCloud est son affaire. Le prix, c'est
une autorisation macOS et une limite : ça ne tourne que sur ce Mac.

Le rattachement d'un événement à sa clé passe par le champ URL, sous la forme
`schema://cle`. EventKit ne laisse pas choisir l'UID d'un événement, et une
table de correspondance à côté se désynchronise dès qu'on efface un événement à
la main ; le champ URL, lui, voyage avec l'événement, iCloud compris.

L'autorisation est accordée à l'application **responsable** du processus. Un
script lancé depuis Terminal se voit demander l'accès au nom de Terminal ; lancé
depuis une application sans clé d'usage du calendrier (VS Code, un agent), la
demande est refusée sans fenêtre. C'est ce que dit `AccesRefuseError`.
"""

import threading
import time
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from icalsync.modeles import (
    FUSEAU_PAR_DEFAUT,
    AccesRefuseError,
    AgendaError,
    Bilan,
    Calendrier,
    CalendrierIntrouvableError,
    Evenement,
    verifier_schema,
)
from icalsync.plan import Planificateur, bornes

try:
    import EventKit
    from Foundation import NSURL, NSDate, NSRunLoop
except ImportError:  # pragma: no cover — hors macOS, ou sans pyobjc
    EventKit = None

__all__ = ["Agenda", "ConvertisseurEK"]

_MODE_BOUCLE = "kCFRunLoopDefaultMode"
_UNE_SECONDE = timedelta(seconds=1)
_REFUS = (
    "macOS a refusé l'accès au calendrier (réponse : {reponse}). Si aucune fenêtre n'est "
    "apparue, l'application qui a lancé ce processus ne déclare pas l'usage du calendrier : "
    "relancer depuis Terminal.app. Sinon, voir Réglages Système › Confidentialité › Calendriers."
)


def _minuit(jour: date, fuseau: ZoneInfo) -> datetime:
    return datetime(jour.year, jour.month, jour.day, tzinfo=fuseau)


def _vers_nsdate(instant: datetime) -> Any:
    return NSDate.dateWithTimeIntervalSince1970_(instant.timestamp())


def _depuis_nsdate(valeur: Any, fuseau: ZoneInfo) -> datetime:
    # NSDate compte en secondes flottantes : l'arrondi efface le bruit binaire.
    return datetime.fromtimestamp(round(valeur.timeIntervalSince1970()), tz=fuseau)


class ConvertisseurEK:
    """Traduit un `Evenement` en champs d'`EKEvent`, et inversement."""

    def __init__(self, fuseau: ZoneInfo = FUSEAU_PAR_DEFAUT) -> None:
        self._fuseau = fuseau

    def appliquer(self, objet: Any, evenement: Evenement, schema: str) -> None:
        situe = evenement.en_fuseau(self._fuseau)
        objet.setTitle_(situe.titre)
        objet.setLocation_(situe.lieu or None)
        objet.setNotes_(situe.notes or None)
        objet.setURL_(NSURL.URLWithString_(f"{schema}://{situe.cle}"))
        if isinstance(situe.debut, datetime) and isinstance(situe.fin, datetime):
            objet.setAllDay_(False)
            objet.setStartDate_(_vers_nsdate(situe.debut))
            objet.setEndDate_(_vers_nsdate(situe.fin))
        else:
            # Journée entière : Calendar attend une fin à 23:59:59 du dernier
            # jour, pas au minuit suivant, qui déborderait d'un jour.
            objet.setAllDay_(True)
            objet.setStartDate_(_vers_nsdate(_minuit(situe.debut, self._fuseau)))
            fin_incluse = _minuit(situe.fin + timedelta(days=1), self._fuseau) - _UNE_SECONDE
            objet.setEndDate_(_vers_nsdate(fin_incluse))

    def vers_evenement(self, objet: Any, cle: str) -> Evenement:
        debut = _depuis_nsdate(objet.startDate(), self._fuseau)
        fin = _depuis_nsdate(objet.endDate(), self._fuseau)
        champs = {
            "cle": cle,
            "titre": str(objet.title() or ""),
            "lieu": str(objet.location() or ""),
            "notes": str(objet.notes() or ""),
        }
        if objet.isAllDay():
            # EventKit rend une fin à 23:59:59 du dernier jour ; reculer d'une
            # seconde couvre aussi un magasin qui la donnerait au minuit suivant.
            dernier = max(debut.date(), (fin - _UNE_SECONDE).date())
            return Evenement(debut=debut.date(), fin=dernier, **champs)
        return Evenement(debut=debut, fin=fin, **champs)


class Agenda:
    """Le magasin d'événements de Calendar, vu par clés."""

    def __init__(self, magasin: Any, fuseau: ZoneInfo = FUSEAU_PAR_DEFAUT) -> None:
        self._magasin = magasin
        self._fuseau = fuseau
        self._convertisseur = ConvertisseurEK(fuseau)

    @classmethod
    def ouvrir(cls, fuseau: ZoneInfo = FUSEAU_PAR_DEFAUT, delai: float = 120.0) -> "Agenda":
        """Demande l'accès complet au calendrier et attend la réponse, `delai` secondes au plus."""
        if EventKit is None:
            raise AgendaError("pyobjc-framework-EventKit manquant : pip install 'icalsync[mac]'")
        magasin = EventKit.EKEventStore.alloc().init()
        fini = threading.Event()
        reponse: dict[str, Any] = {}

        def rappel(accorde: bool, erreur: Any) -> None:
            reponse["accorde"] = bool(accorde)
            reponse["erreur"] = erreur
            fini.set()

        if hasattr(magasin, "requestFullAccessToEventsWithCompletion_"):
            magasin.requestFullAccessToEventsWithCompletion_(rappel)
        else:  # pragma: no cover — macOS 13 et avant
            magasin.requestAccessToEntityType_completion_(EventKit.EKEntityTypeEvent, rappel)
        limite = time.monotonic() + delai
        # La réponse arrive par la boucle d'exécution : il faut la faire tourner.
        while not fini.is_set() and time.monotonic() < limite:
            NSRunLoop.currentRunLoop().runMode_beforeDate_(
                _MODE_BOUCLE, NSDate.dateWithTimeIntervalSinceNow_(0.2)
            )
        if not fini.is_set():
            raise AccesRefuseError(f"pas de réponse en {delai:.0f} s")
        if not reponse["accorde"]:
            raise AccesRefuseError(_REFUS.format(reponse=reponse["erreur"] or "aucune erreur"))
        return cls(magasin, fuseau)

    def calendriers(self) -> list[Calendrier]:
        return [
            Calendrier(
                nom=str(objet.title()),
                source=str(objet.source().title()) if objet.source() else "",
                modifiable=bool(objet.allowsContentModifications()),
            )
            for objet in self._objets_calendriers()
        ]

    def lire(self, calendrier: str, schema: str, debut: date, fin: date) -> list[Evenement]:
        """Les événements du schéma entre `debut` et `fin` inclus."""
        verifier_schema(schema)
        objet = self._calendrier(calendrier)
        return [
            self._convertisseur.vers_evenement(trouve, cle)
            for cle, trouve in self._marques(objet, schema, debut, fin)
        ]

    def synchroniser(
        self,
        calendrier: str,
        evenements: Sequence[Evenement],
        schema: str,
        debut: date | None = None,
        fin: date | None = None,
        supprimer_orphelins: bool = True,
    ) -> Bilan:
        """Rend le calendrier égal à `evenements` sur la fenêtre, et valide en une fois.

        La fenêtre est celle des événements attendus, élargie à `debut` et `fin`
        s'ils sont donnés. Ce qui la déborde n'est ni lu ni touché : pour retirer
        une séance qui n'a plus d'équivalent, il faut que la fenêtre la couvre.
        """
        verifier_schema(schema)
        objet = self._calendrier(calendrier)
        souhaites = [evenement.en_fuseau(self._fuseau) for evenement in evenements]
        debut, fin = self._fenetre(souhaites, debut, fin)

        existants: dict[str, Evenement] = {}
        objets: dict[str, Any] = {}
        doublons: list[tuple[str, Any]] = []
        for cle, trouve in self._marques(objet, schema, debut, fin):
            if cle in objets:
                doublons.append((cle, trouve))
                continue
            objets[cle] = trouve
            existants[cle] = self._convertisseur.vers_evenement(trouve, cle)

        plan = Planificateur(supprimer_orphelins).etablir(existants, souhaites)
        for evenement in plan.a_creer:
            nouveau = EventKit.EKEvent.eventWithEventStore_(self._magasin)
            nouveau.setCalendar_(objet)
            self._convertisseur.appliquer(nouveau, evenement, schema)
            self._enregistrer(nouveau)
        for evenement in plan.a_modifier:
            self._convertisseur.appliquer(objets[evenement.cle], evenement, schema)
            self._enregistrer(objets[evenement.cle])
        for cle in plan.a_supprimer:
            self._retirer(objets[cle])
        # Un doublon de clé vient d'un import répété : il part avec les orphelins.
        supprimes = list(plan.a_supprimer)
        if supprimer_orphelins:
            for cle, trouve in doublons:
                self._retirer(trouve)
                supprimes.append(cle)
        self._valider()
        return Bilan(
            crees=tuple(evenement.cle for evenement in plan.a_creer),
            modifies=tuple(evenement.cle for evenement in plan.a_modifier),
            supprimes=tuple(supprimes),
            inchanges=plan.inchanges,
        )

    def purger(self, calendrier: str, schema: str, debut: date, fin: date) -> int:
        """Retire tous les événements du schéma sur la fenêtre ; rend leur nombre."""
        verifier_schema(schema)
        objet = self._calendrier(calendrier)
        trouves = self._marques(objet, schema, debut, fin)
        for _, trouve in trouves:
            self._retirer(trouve)
        self._valider()
        return len(trouves)

    # -- Accès au magasin --------------------------------------------------

    def _objets_calendriers(self) -> list[Any]:
        return list(self._magasin.calendarsForEntityType_(EventKit.EKEntityTypeEvent))

    def _calendrier(self, nom: str) -> Any:
        candidats = [objet for objet in self._objets_calendriers() if str(objet.title()) == nom]
        if not candidats:
            noms = ", ".join(sorted({str(objet.title()) for objet in self._objets_calendriers()}))
            raise CalendrierIntrouvableError(f"aucun calendrier nommé « {nom} » ; il y a : {noms}")
        modifiables = [objet for objet in candidats if objet.allowsContentModifications()]
        if not modifiables:
            raise CalendrierIntrouvableError(f"« {nom} » n'est pas modifiable")
        if len(modifiables) > 1:
            raise CalendrierIntrouvableError(f"plusieurs calendriers modifiables nommés « {nom} »")
        return modifiables[0]

    def _fenetre(
        self, souhaites: Sequence[Evenement], debut: date | None, fin: date | None
    ) -> tuple[date, date]:
        if souhaites:
            premier, dernier = bornes(souhaites)
            return (
                premier if debut is None else min(debut, premier),
                dernier if fin is None else max(fin, dernier),
            )
        if debut is None or fin is None:
            raise ValueError("sans événement attendu, il faut donner debut et fin")
        return debut, fin

    def _marques(self, objet: Any, schema: str, debut: date, fin: date) -> list[tuple[str, Any]]:
        """Les événements du calendrier dont l'URL commence par `schema://`, avec leur clé."""
        prefixe = f"{schema}://"
        predicat = self._magasin.predicateForEventsWithStartDate_endDate_calendars_(
            _vers_nsdate(_minuit(debut, self._fuseau)),
            _vers_nsdate(_minuit(fin + timedelta(days=1), self._fuseau)),
            [objet],
        )
        trouves: list[tuple[str, Any]] = []
        for candidat in self._magasin.eventsMatchingPredicate_(predicat) or []:
            url = candidat.URL()
            if url is None:
                continue
            texte = str(url.absoluteString())
            if texte.startswith(prefixe):
                trouves.append((texte[len(prefixe) :], candidat))
        return trouves

    def _enregistrer(self, objet: Any) -> None:
        ok, erreur = self._magasin.saveEvent_span_commit_error_(
            objet, EventKit.EKSpanThisEvent, False, None
        )
        if not ok:
            raise AgendaError(f"enregistrement refusé : {erreur}")

    def _retirer(self, objet: Any) -> None:
        ok, erreur = self._magasin.removeEvent_span_commit_error_(
            objet, EventKit.EKSpanThisEvent, False, None
        )
        if not ok:
            raise AgendaError(f"suppression refusée : {erreur}")

    def _valider(self) -> None:
        ok, erreur = self._magasin.commit_(None)
        if not ok:
            raise AgendaError(f"validation refusée : {erreur}")
