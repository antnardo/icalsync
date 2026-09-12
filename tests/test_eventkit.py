"""Conversions vers et depuis EKEvent, sans toucher au calendrier.

Créer un `EKEvent` en mémoire ne demande aucune autorisation : seuls
l'enregistrement et la lecture du magasin en demandent une. C'est donc la
partie de `eventkit` qui se teste partout où pyobjc est installé.
"""

from dataclasses import replace
from datetime import date

import pytest

from icalsync.modeles import FUSEAU_PAR_DEFAUT, Evenement

EventKit = pytest.importorskip("EventKit")

from icalsync.eventkit import ConvertisseurEK  # noqa: E402 — après importorskip


@pytest.fixture(scope="module")
def magasin():
    return EventKit.EKEventStore.alloc().init()


@pytest.fixture
def convertisseur():
    return ConvertisseurEK(FUSEAU_PAR_DEFAUT)


def _aller_retour(magasin, convertisseur, evenement):
    objet = EventKit.EKEvent.eventWithEventStore_(magasin)
    convertisseur.appliquer(objet, evenement, "essai")
    return objet, convertisseur.vers_evenement(objet, evenement.cle)


class TestConvertisseurEK:
    def test_horaire_revient_identique(self, magasin, convertisseur, horaire):
        _, relu = _aller_retour(magasin, convertisseur, horaire)
        assert relu == horaire.en_fuseau(FUSEAU_PAR_DEFAUT)

    def test_journee_revient_identique(self, magasin, convertisseur, journee):
        _, relu = _aller_retour(magasin, convertisseur, journee)
        assert relu == journee

    def test_journee_est_marquee_journee_entiere(self, magasin, convertisseur, journee):
        objet, _ = _aller_retour(magasin, convertisseur, journee)
        assert objet.isAllDay()

    def test_url_porte_le_schema_et_la_cle(self, magasin, convertisseur, horaire):
        objet, _ = _aller_retour(magasin, convertisseur, horaire)
        assert str(objet.URL().absoluteString()) == "essai://seance/12"

    def test_champs_vides_reviennent_vides(self, magasin, convertisseur, horaire):
        nu = replace(horaire, lieu="", notes="")
        _, relu = _aller_retour(magasin, convertisseur, nu)
        assert (relu.lieu, relu.notes) == ("", "")

    def test_fin_posee_au_minuit_suivant_deborde_d_un_jour(self, magasin, convertisseur):
        """EventKit ramène toute fin de journée entière à 23:59:59 du jour qui la contient.

        Une fin au minuit suivant tombe donc dans le lendemain, et l'événement
        s'allonge d'un jour : c'est pourquoi `appliquer` écrit 23:59:59.
        """
        objet = EventKit.EKEvent.eventWithEventStore_(magasin)
        convertisseur.appliquer(
            objet, Evenement("j", "J", date(2026, 3, 2), date(2026, 3, 2)), "essai"
        )
        objet.setEndDate_(objet.endDate().dateByAddingTimeInterval_(1))
        assert convertisseur.vers_evenement(objet, "j").fin == date(2026, 3, 3)
