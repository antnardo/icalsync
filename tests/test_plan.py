from dataclasses import replace
from datetime import date, datetime

import pytest

from icalsync.modeles import CleDupliqueeError, Evenement
from icalsync.plan import Planificateur, bornes, indexer


@pytest.fixture
def planificateur():
    return Planificateur()


class TestPlanificateur:
    def test_inconnu_est_a_creer(self, planificateur, horaire):
        plan = planificateur.etablir({}, [horaire])
        assert plan.a_creer == (horaire,)
        assert plan.vide is False

    def test_identique_est_inchange(self, planificateur, horaire):
        plan = planificateur.etablir({horaire.cle: horaire}, [horaire])
        assert plan.inchanges == (horaire.cle,)
        assert plan.vide is True

    def test_champ_different_est_a_modifier(self, planificateur, horaire):
        deplace = replace(horaire, debut=datetime(2026, 9, 14, 9, 0))
        plan = planificateur.etablir({horaire.cle: horaire}, [deplace])
        assert plan.a_modifier == (deplace,)

    def test_orphelin_est_a_supprimer(self, planificateur, horaire, journee):
        plan = planificateur.etablir({horaire.cle: horaire, journee.cle: journee}, [horaire])
        assert plan.a_supprimer == (journee.cle,)

    def test_orphelin_garde_sur_demande(self, horaire, journee):
        prudent = Planificateur(supprimer_orphelins=False)
        plan = prudent.etablir({journee.cle: journee}, [horaire])
        assert plan.a_supprimer == ()
        assert plan.a_creer == (horaire,)

    def test_cle_en_double_est_refusee(self, planificateur, horaire):
        with pytest.raises(CleDupliqueeError):
            planificateur.etablir({}, [horaire, replace(horaire, titre="Autre")])


class TestIndexer:
    def test_conserve_l_ordre_d_arrivee(self, horaire, journee):
        assert list(indexer([journee, horaire])) == [journee.cle, horaire.cle]


class TestBornes:
    def test_couvre_du_premier_au_dernier_jour(self, horaire, journee):
        assert bornes([journee, horaire]) == (date(2026, 9, 14), date(2027, 4, 30))

    def test_vide_est_une_erreur(self):
        with pytest.raises(ValueError, match="aucun événement"):
            bornes([])

    def test_un_instant_compte_pour_son_jour(self):
        tard = Evenement("x", "X", datetime(2026, 1, 1, 23), datetime(2026, 1, 2, 1))
        assert bornes([tard]) == (date(2026, 1, 1), date(2026, 1, 2))
