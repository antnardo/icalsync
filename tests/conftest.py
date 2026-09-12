from datetime import date, datetime

import pytest

from icalsync.modeles import FUSEAU_PAR_DEFAUT, Evenement


@pytest.fixture
def paris():
    return FUSEAU_PAR_DEFAUT


@pytest.fixture
def horaire():
    return Evenement(
        cle="seance/12",
        titre="Cours",
        debut=datetime(2026, 9, 14, 8, 0),
        fin=datetime(2026, 9, 14, 10, 0),
        lieu="Salle 12",
        notes="Chapitre 3",
    )


@pytest.fixture
def journee():
    return Evenement(
        cle="examens/ecrits",
        titre="Écrits",
        debut=date(2027, 4, 26),
        fin=date(2027, 4, 30),
    )
