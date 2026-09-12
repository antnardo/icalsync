from dataclasses import replace

import pytest
from icalendar import Calendar

from icalsync.ics import ExportICS
from icalsync.modeles import CleDupliqueeError, CleInvalideError


@pytest.fixture
def export():
    return ExportICS(schema="cahiertexte", nom_calendrier="Cours 2026-2027")


def _evenements(contenu: bytes):
    return list(Calendar.from_ical(contenu).walk("VEVENT"))


class TestExportICS:
    def test_schema_invalide_est_refuse(self):
        with pytest.raises(CleInvalideError):
            ExportICS(schema="1abc")

    def test_uid_et_url_derivent_de_la_cle(self, export, horaire):
        (vevent,) = _evenements(export.composer([horaire]))
        assert str(vevent["UID"]) == "seance/12@cahiertexte"
        assert str(vevent["URL"]) == "cahiertexte://seance/12"

    def test_instant_porte_le_fuseau(self, export, horaire):
        contenu = export.composer([horaire])
        assert b"DTSTART;TZID=Europe/Paris:20260914T080000" in contenu
        assert b"BEGIN:VTIMEZONE" in contenu

    def test_journee_entiere_a_une_fin_exclusive(self, export, journee):
        contenu = export.composer([journee])
        assert b"DTSTART;VALUE=DATE:20270426" in contenu
        assert b"DTEND;VALUE=DATE:20270501" in contenu

    def test_lieu_et_notes_sont_repris(self, export, horaire):
        (vevent,) = _evenements(export.composer([horaire]))
        assert str(vevent["LOCATION"]) == "Salle 12"
        assert str(vevent["DESCRIPTION"]) == "Chapitre 3"

    def test_champs_vides_sont_omis(self, export, journee):
        (vevent,) = _evenements(export.composer([journee]))
        assert "LOCATION" not in vevent
        assert "DESCRIPTION" not in vevent

    def test_nom_de_calendrier_est_ecrit(self, export, horaire):
        assert b"X-WR-CALNAME:Cours 2026-2027" in export.composer([horaire])

    def test_cle_en_double_est_refusee(self, export, horaire):
        with pytest.raises(CleDupliqueeError):
            export.composer([horaire, replace(horaire, titre="Autre")])

    def test_ecrire_pose_le_fichier(self, export, horaire, journee, tmp_path):
        fichier = tmp_path / "export.ics"
        contenu = export.ecrire([horaire, journee], fichier)
        assert fichier.read_bytes() == contenu
        assert len(_evenements(contenu)) == 2
