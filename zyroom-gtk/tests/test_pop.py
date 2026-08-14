"""La table de pop : ce qui sort, et par quel temps.

Elle n'est plus relevée à la main. Elle se déduit de deux sources que l'on peut
confronter — le relevé de Ryzom Armory pour le couple saison × zone, et la
fourchette d'humidité que le tracker d'atys.us donne pour chaque gisement.

Ce que ces contrôles tiennent : la table dit **exactement** ce que ces deux
sources disent, ni plus ni moins. Le classeur de la guilde, qu'elle remplace,
donnait souvent trois conditions là où le jeu en donne deux, et ne s'accordait
avec l'humidité du jeu que sur une matière sur quarante-six.
"""

import collections
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, meteo                                  # noqa: E402
from zyroom.pop import POP, CONTINENT_DE_ZONE                     # noqa: E402

#: Le générateur, qui sait rapprocher le français de l'écran de l'anglais du
#: tracker. Il vit du côté Android, où sont tous les outils : les deux contrôles
#: qui en dépendent se passent si l'on ne travaille que sur le portage GTK.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "zyroom-android", "outils"))
try:
    from table_gisements import (FAMILLE_CORRIGEE, FAMILLES_FR,   # noqa: E402
                                 MATIERES_FR, normalise)
    OUTILS = True
except ImportError:                                     # pragma: no cover
    OUTILS = False

#: Le fichier des fourchettes, hors du portage : les deux applications le
#: partagent, et c'est `outils/humidites.py` qui le remplit.
HUMIDITES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))),
    "donnees", "humidites-gisements.json")

#: Les quatre bandes du jeu, par humidité croissante. Sec vaut mieux qu'humide.
BANDES = ((0.0, 16.6, "BEST"), (16.7, 49.9, "GOOD"),
          (50.0, 83.3, "BAD"), (83.4, 100.0, "WORST"))


def fourchettes() -> dict:
    with open(HUMIDITES, encoding="utf-8") as fh:
        return json.load(fh)["humidites"]


class Structure(unittest.TestCase):

    def test_les_quatre_saisons_et_les_quatre_zones(self):
        self.assertEqual(set(meteo.SAISONS), set(POP))
        for saison, zones in POP.items():
            self.assertEqual(set(CONTINENT_DE_ZONE), set(zones), saison)

    def test_les_quatre_conditions_sont_partout(self):
        """Une case vide voudrait dire « rien ne sort », ce qui n'arrive pas.

        C'était le défaut du classeur : ses trous se lisaient comme des
        absences."""
        for saison, zones in POP.items():
            for zone, conditions in zones.items():
                self.assertEqual({"WORST", "BAD", "GOOD", "BEST"},
                                 set(conditions), f"{saison} / {zone}")


class DeuxConditionsParMatiere(unittest.TestCase):
    """Le jeu range l'humidité en quatre bandes, chaque gisement en occupe deux."""

    def test_chaque_matiere_sort_par_deux_conditions(self):
        for saison, zones in POP.items():
            for zone, conditions in zones.items():
                compte = collections.Counter()
                for familles in conditions.values():
                    for famille, matieres in familles.items():
                        for matiere in matieres:
                            compte[(famille, matiere)] += 1
                for couple, n in compte.items():
                    self.assertEqual(2, n, f"{saison} / {zone} / {couple}")

    @unittest.skipUnless(OUTILS, "outils/ absent")
    def test_les_conditions_suivent_la_fourchette_d_humidite(self):
        """La table ne fait que traduire l'humidité : on le revérifie ici.

        Sans ce contrôle, une erreur de bande dans le générateur produirait une
        table cohérente avec elle-même et fausse pour le joueur."""
        humidites = fourchettes()
        for saison, zones in POP.items():
            for zone, conditions in zones.items():
                for condition, familles in conditions.items():
                    for famille, matieres in familles.items():
                        for matiere in matieres:
                            vraie = FAMILLE_CORRIGEE.get(matiere, famille)
                            cle = (f"supreme|{FAMILLES_FR[vraie]}"
                                   f"|{MATIERES_FR[normalise(matiere)]}")
                            plages = humidites[cle]
                            attendu = {c for bas, haut, c in BANDES
                                       if any(p0 <= bas and haut <= p1
                                              for p0, p1 in plages)}
                            self.assertIn(condition, attendu,
                                          f"{famille}/{matiere} en {condition} "
                                          f"alors que {plages}")


class FideleAArmory(unittest.TestCase):

    @unittest.skipUnless(OUTILS, "outils/ absent")
    def test_la_table_ne_contient_que_ce_qu_armory_donne(self):
        for saison, zones in POP.items():
            for zone, conditions in zones.items():
                attendu = {(f, normalise(m))
                           for f, ms in armory.SUPREMES[saison][zone].items()
                           for m in ms}
                trouve = {(f, m) for familles in conditions.values()
                          for f, ms in familles.items() for m in ms}
                self.assertEqual(attendu, trouve, f"{saison} / {zone}")


if __name__ == "__main__":
    unittest.main()
