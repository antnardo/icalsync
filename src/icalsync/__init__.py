"""icalsync — des événements à clé stable, posés dans un agenda et tenus à jour.

Deux sorties pour un même modèle : `Agenda` écrit dans Calendar sous macOS, et
`ExportICS` produit un fichier iCalendar. Dans les deux cas, l'événement porte
`schema://cle` dans son champ URL, ce qui permet de le retrouver au passage
suivant au lieu d'en créer un autre.
"""

from icalsync.eventkit import Agenda, ConvertisseurEK
from icalsync.ics import ExportICS
from icalsync.modeles import (
    FUSEAU_PAR_DEFAUT,
    AccesRefuseError,
    AgendaError,
    Bilan,
    Calendrier,
    CalendrierIntrouvableError,
    CleDupliqueeError,
    CleInvalideError,
    Evenement,
    verifier_schema,
)
from icalsync.plan import Plan, Planificateur, bornes, indexer

__version__ = "0.1.0"

__all__ = [
    "FUSEAU_PAR_DEFAUT",
    "AccesRefuseError",
    "Agenda",
    "AgendaError",
    "Bilan",
    "Calendrier",
    "CalendrierIntrouvableError",
    "CleDupliqueeError",
    "CleInvalideError",
    "ConvertisseurEK",
    "Evenement",
    "ExportICS",
    "Plan",
    "Planificateur",
    "__version__",
    "bornes",
    "indexer",
    "verifier_schema",
]
