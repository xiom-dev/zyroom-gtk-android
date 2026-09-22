"""La table de forage : ce que rend un gisement des Primes, où et quand.

Elle est fabriquée par `outils/table_forage.py`, qui croise `armory.py` et les
fourchettes d'humidité de `donnees/humidites-gisements.json`. **Les deux
viennent du tracker d'atys.us**, et c'est tout l'enjeu : c'est le tracker qu'on
ouvre à côté de l'application pour vérifier, et une table qui ne lui répond pas
est fausse, si cohérente soit-elle avec elle-même.

Le contrôle qui refait le calcul du tracker matière pour matière est dans
`test_meteo.py`, avec le reste de l'écran météo. Ici, on tient la forme de la
table et la frontière qu'elle ne doit pas franchir : les excellentes des
continents ne sont pas celles des Primes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, forage, meteo                          # noqa: E402

SAISONS = set(meteo.SAISONS)
CONDITIONS = {"WORST", "BAD", "GOOD", "BEST"}


def matieres_des_primes() -> set:
    """Les couples (famille, matière) qu'Armory place dans les Primes."""
    return {(famille, matiere)
            for zones in armory.SUPREMES.values()
            for familles in zones.values()
            for famille, matieres in familles.items()
            for matiere in matieres}


class Structure(unittest.TestCase):

    def test_les_quatre_zones_des_primes(self):
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            self.assertEqual(set(meteo.ZONES), set(table), quoi)

    def test_les_noms_sont_ceux_d_armory(self):
        """Un nom qui ne se rejoint pas disparaîtrait de l'écran sans un mot."""
        attendu = matieres_des_primes()
        self.assertEqual(47, len(attendu))
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            for zone, matieres in table.items():
                self.assertLessEqual(set(matieres), attendu, f"{quoi}/{zone}")

    def test_les_créneaux_sont_bien_formés(self):
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            for zone, matieres in table.items():
                for couple, creneaux in matieres.items():
                    self.assertTrue(creneaux, f"{quoi}/{zone}/{couple}")
                    for saison, condition in creneaux:
                        self.assertIn(saison, SAISONS, couple)
                        self.assertIn(condition, CONDITIONS, couple)

    def test_le_choix_reste_vide(self):
        """Aucune source ne le suit.

        Le déduire par élimination — ce qui n'est ni suprême ni excellente —
        ferait dire à l'écran plus que ce qu'on sait : le tutoriel de la guilde
        écrit qu'une saison peut n'avoir aucun pop de choix."""
        self.assertEqual({zone: {} for zone in meteo.ZONES}, forage.CHOIX)


class ChaqueGisementOccupeDeuxBandes(unittest.TestCase):
    """La règle du jeu, mesurée sur l'API : deux bandes d'humidité sur quatre.

    C'est elle qui fait qu'il sort toujours quelque chose, et qu'il n'en sort
    jamais tout.
    """

    def test_deux_conditions_par_matière_et_par_saison(self):
        for zone, matieres in forage.SUPREMES.items():
            for couple, creneaux in matieres.items():
                par_saison = {}
                for saison, condition in creneaux:
                    par_saison.setdefault(saison, set()).add(condition)
                for saison, conditions in par_saison.items():
                    self.assertEqual(2, len(conditions),
                                     f"{zone}/{couple}/{saison}")

    def test_une_moitié_des_matières_sort_à_chaque_instant(self):
        for saison in range(4):
            for condition in CONDITIONS:
                for zone in meteo.ZONES:
                    _q, groupes = meteo.sortie_de(saison, zone, condition)
                    n = sum(len(m) for m in groupes.values())
                    self.assertTrue(10 <= n <= 30,
                                    f"{zone} / {condition} : {n}")


class LesContinentsRestentÀPart(unittest.TestCase):
    """L'onglet des excellentes du tutoriel ne parle pas des Primes.

    Il est lu — il s'accorde sur quarante-cinq matières avec les fourchettes du
    tracker, ce qui le rend crédible — mais ses gisements sont au Gouffre
    d'Ichor ou à la Porte des Vents. Les afficher sous « Sources Interdites »
    enverrait la joueuse forer au mauvais bout d'Atys.
    """

    def test_quarante_sept_matières_deux_saisons_deux_conditions(self):
        self.assertEqual(47, len(forage.EXCELLENTES_CONTINENTS))
        for couple, creneaux in forage.EXCELLENTES_CONTINENTS.items():
            self.assertEqual(4, len(creneaux), couple)
            self.assertEqual(2, len({s for s, _c in creneaux}), couple)

    def test_l_écran_ne_l_affiche_pas(self):
        """`sortie_de` ne lit que les trois tables des Primes."""
        for zone in meteo.ZONES:
            for saison in range(4):
                for condition in CONDITIONS:
                    _q, groupes = meteo.sortie_de(saison, zone, condition)
                    trouve = {(f, m) for f, ms in groupes.items() for m in ms}
                    dans_la_table = (set(forage.SUPREMES[zone])
                                     | set(forage.EXCELLENTES[zone]))
                    self.assertLessEqual(trouve, dans_la_table, zone)


if __name__ == "__main__":
    unittest.main()
