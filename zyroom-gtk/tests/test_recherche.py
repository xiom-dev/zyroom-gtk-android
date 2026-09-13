"""Le découpage d'une requête de recherche : le nom d'un côté, les qualités de l'autre."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom.models import decouper_recherche, famille_matiere       # noqa: E402


class Decoupage(unittest.TestCase):

    def test_un_nom_et_une_qualite(self):
        self.assertEqual(("oeil", {220}), decouper_recherche("oeil 220"))

    def test_plusieurs_qualites(self):
        self.assertEqual(("ongle", {250, 270}),
                         decouper_recherche("ongle 270 250"))

    def test_une_qualite_seule_garde_le_nom_vide(self):
        """Pour voir d'un coup tout ce qu'on a dans cette qualité."""
        self.assertEqual(("", {250}), decouper_recherche("250"))

    def test_un_nombre_colle_a_des_lettres_reste_du_texte(self):
        """Sinon un nom d'item portant un chiffre deviendrait introuvable."""
        self.assertEqual(("q250", set()), decouper_recherche("q250"))
        self.assertEqual(("mp2", set()), decouper_recherche("mp2"))

    def test_les_espaces_en_trop_disparaissent(self):
        self.assertEqual(("oeil", set()), decouper_recherche("  oeil  "))
        self.assertEqual(("", set()), decouper_recherche(""))


if __name__ == "__main__":
    unittest.main()


class Familles(unittest.TestCase):
    """`famille_matiere` : la famille se lit avant la classe, pas au premier mot."""

    def test_la_classe_borne_la_famille(self):
        self.assertEqual("Résine", famille_matiere("Résine de base de Colle"))
        self.assertEqual("Graine", famille_matiere("Graine de base / Caprice"))

    def test_une_famille_de_plusieurs_mots(self):
        """Le premier mot seul donnerait « Bout », « Fragment », « Mesure »."""
        self.assertEqual("Bout de chair",
                         famille_matiere("Bout de chair exceptionnelle / Cray"))
        self.assertEqual("Fragment d'épine",
                         famille_matiere("Fragment d'épine fine / Arma"))
        self.assertEqual("Mesure de sève",
                         famille_matiere("Mesure de sève de base / Ardente"))

    def test_l_espece_apres_la_barre_ne_compte_pas(self):
        self.assertEqual("Petite feuille",
                         famille_matiere("Petite feuille / Roseau ordinaire"))
        self.assertEqual("Ongle", famille_matiere("Ongle de base /  / Bodoc"))

    def test_sans_nom_pas_de_famille(self):
        """Sans le pack, un item ne porte que son code de fiche."""
        self.assertEqual("", famille_matiere(""))
