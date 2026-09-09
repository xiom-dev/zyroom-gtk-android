#!/usr/bin/env python3
"""Les noms de dossier de la mise a jour ne s'empilent pas.

Un joueur s'est retrouve avec `ZyRoom-Qt`, `ZyRoom-Qt.nouveau` et
`ZyRoom-Qt.nouveau.nouveau` : la mise en place n'avait pas eu lieu, il avait
lance l'application depuis le dossier depose a cote, et la mise a jour
suivante avait colle un second suffixe au premier.

Ces controles tournent sur n'importe quel systeme : ils ne portent que sur le
calcul des noms, qui est justement ce qui avait lache.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import updater  # noqa: E402


class Suffixes(unittest.TestCase):
    """Le dossier de base se retrouve quel que soit l'empilement."""

    def test_sans_suffixe(self):
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt"),
                         "/o/ZyRoom-Qt")

    def test_un_suffixe(self):
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt.nouveau"),
                         "/o/ZyRoom-Qt")

    def test_suffixes_empiles(self):
        self.assertEqual(
            updater.dossier_canonique("/o/ZyRoom-Qt.nouveau.nouveau"),
            "/o/ZyRoom-Qt")

    def test_melange(self):
        self.assertEqual(
            updater.dossier_canonique("/o/ZyRoom-Qt.ancien.nouveau"),
            "/o/ZyRoom-Qt")

    def test_un_point_qui_n_est_pas_a_nous(self):
        """Un dossier nomme autrement garde son nom."""
        self.assertEqual(updater.dossier_canonique("/o/ZyRoom-Qt.1.11"),
                         "/o/ZyRoom-Qt.1.11")


class ChezSoi(unittest.TestCase):
    """On sait dire qu'on tourne depuis un dossier depose a cote."""

    def _poser(self, dossier):
        updater.dossier_installe = lambda: dossier

    def setUp(self):
        self._vrai = updater.dossier_installe
        self.addCleanup(lambda: setattr(updater, "dossier_installe",
                                        self._vrai))

    def test_chez_soi(self):
        self._poser("/o/ZyRoom-Qt")
        self.assertFalse(updater.hors_de_chez_soi())

    def test_ailleurs(self):
        self._poser("/o/ZyRoom-Qt.nouveau")
        self.assertTrue(updater.hors_de_chez_soi())

    def test_hors_paquet(self):
        """Depuis les sources, il n'y a pas d'installation : rien a dire."""
        self._poser("")
        self.assertFalse(updater.hors_de_chez_soi())


if __name__ == "__main__":
    unittest.main()
