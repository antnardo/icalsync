"""Aller-retour de contrôle dans un calendrier réel : créer, relire, déplacer, retirer.

À lancer depuis Terminal.app, l'autorisation macOS lui étant rattachée :

    python examples/aller_retour.py Perso

Tout ce qui est posé porte le schéma `icalsync-essai` et repart à la fin, y
compris si une étape échoue.
"""

import sys
from dataclasses import replace
from datetime import date, datetime, timedelta

from icalsync import FUSEAU_PAR_DEFAUT, Agenda, Evenement

SCHEMA = "icalsync-essai"


def main(calendrier: str) -> int:
    agenda = Agenda.ouvrir()
    aujourd_hui = date.today()
    fenetre = {"debut": aujourd_hui - timedelta(days=1), "fin": aujourd_hui + timedelta(days=2)}
    dans_une_heure = (datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0)
    horaire = Evenement(
        "essai/horaire",
        "icalsync — essai horaire",
        dans_une_heure,
        dans_une_heure + timedelta(minutes=30),
        lieu="Salle d'essai",
        notes="Posé par examples/aller_retour.py ; retiré à la fin du script.",
    )
    journee = Evenement("essai/journee", "icalsync — essai journée", aujourd_hui, aujourd_hui)

    try:
        print("1. création          :", agenda.synchroniser(calendrier, [horaire, journee], SCHEMA))
        relus = agenda.lire(calendrier, SCHEMA, **fenetre)
        for evenement in relus:
            print("   relu :", evenement)
        print("   horaire identique :", horaire.en_fuseau(FUSEAU_PAR_DEFAUT) in relus)
        print("   journée identique :", journee in relus)

        print("2. relance identique :", agenda.synchroniser(calendrier, [horaire, journee], SCHEMA))

        deplace = replace(
            horaire,
            debut=horaire.debut + timedelta(hours=1),
            fin=horaire.fin + timedelta(hours=1),
            titre="icalsync — essai horaire (déplacé)",
        )
        print(
            "3. déplacement, retrait :",
            agenda.synchroniser(calendrier, [deplace], SCHEMA, **fenetre),
        )
        for evenement in agenda.lire(calendrier, SCHEMA, **fenetre):
            print("   relu :", evenement)

        print("4. tout retirer      :", agenda.synchroniser(calendrier, [], SCHEMA, **fenetre))
        print("   reste :", agenda.lire(calendrier, SCHEMA, **fenetre))
    finally:
        restes = agenda.purger(calendrier, SCHEMA, **fenetre)
        print(f"nettoyage final : {restes} événement(s) d'essai retiré(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "Perso"))
