from dataclasses import replace
from datetime import UTC, date, datetime

import pytest

from icalsync.modeles import Bilan, CleInvalideError, verifier_schema


class TestEvenement:
    def test_instants_donnent_un_creneau_horaire(self, horaire):
        assert not horaire.journee_entiere

    def test_dates_donnent_une_journee_entiere(self, journee):
        assert journee.journee_entiere

    def test_bornes_de_jour_sont_incluses(self, journee):
        assert (journee.premier_jour, journee.dernier_jour) == (
            date(2027, 4, 26),
            date(2027, 4, 30),
        )

    @pytest.mark.parametrize("cle", ["", "a b", "clé", "x#1", "a?b"])
    def test_cle_hors_motif_est_refusee(self, horaire, cle):
        with pytest.raises(CleInvalideError):
            replace(horaire, cle=cle)

    @pytest.mark.parametrize("cle", ["seance/12", "oral.2026-06-12_3", "a~b"])
    def test_cle_sure_pour_une_url_est_acceptee(self, horaire, cle):
        assert replace(horaire, cle=cle).cle == cle

    def test_titre_vide_est_refuse(self, horaire):
        with pytest.raises(ValueError, match="titre vide"):
            replace(horaire, titre="  ")

    def test_bornes_de_types_differents_sont_refusees(self, horaire):
        with pytest.raises(ValueError, match="deux instants ou deux dates"):
            replace(horaire, fin=date(2026, 9, 14))

    def test_fin_avant_debut_est_refusee(self, journee):
        with pytest.raises(ValueError, match="précède"):
            replace(journee, fin=date(2027, 4, 25))

    def test_en_fuseau_ancre_un_instant_naif(self, horaire, paris):
        situe = horaire.en_fuseau(paris)
        assert situe.debut.tzinfo is paris
        assert situe.debut.hour == 8

    def test_en_fuseau_convertit_un_instant_situe(self, horaire, paris):
        utc = replace(
            horaire,
            debut=datetime(2026, 9, 14, 6, 0, tzinfo=UTC),
            fin=datetime(2026, 9, 14, 8, 0, tzinfo=UTC),
        )
        assert utc.en_fuseau(paris).debut.hour == 8

    def test_en_fuseau_efface_les_microsecondes(self, horaire, paris):
        bruite = replace(horaire, debut=horaire.debut.replace(microsecond=999_999))
        assert bruite.en_fuseau(paris) == horaire.en_fuseau(paris)

    def test_en_fuseau_laisse_une_journee_entiere_intacte(self, journee, paris):
        assert journee.en_fuseau(paris) is journee


class TestVerifierSchema:
    @pytest.mark.parametrize("schema", ["cahiertexte", "x-oraux", "a1+b.c"])
    def test_schema_conforme_est_rendu(self, schema):
        assert verifier_schema(schema) == schema

    @pytest.mark.parametrize("schema", ["", "1abc", "a b", "é", "a://"])
    def test_schema_non_conforme_est_refuse(self, schema):
        with pytest.raises(CleInvalideError):
            verifier_schema(schema)


class TestBilan:
    def test_vide_se_lit_a_zero(self):
        assert str(Bilan()) == "0 créé, 0 modifié, 0 supprimé, 0 inchangé"

    def test_pluriel_au_dela_de_un(self):
        bilan = Bilan(crees=("a", "b"), modifies=("c",), inchanges=("d", "e", "f"))
        assert str(bilan) == "2 créés, 1 modifié, 0 supprimé, 3 inchangés"
