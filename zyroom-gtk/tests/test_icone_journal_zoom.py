"""L'icône du journal grandit avec le reste.

Le défaut que ces essais gardent : la taille des icônes du journal était
écrite en dur — vingt-quatre pixels —, alors que le zoom commande tout le
reste, y compris la hauteur des lignes. En agrandissant, les lignes
s'écartaient et l'icône restait ; elle paraissait donc rétrécir à mesure
qu'on grossissait l'affichage, ce qui est exactement l'inverse de ce qu'on
demande à un bouton de zoom.

Ce qui doit tenir : le côté de l'icône est une part de celle de l'inventaire,
et il change à chaque cran. C'est de l'arithmétique, donc ça se vérifie sans
écran.
"""

import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import config                                        # noqa: E402
from zyroom.window import MainWindow                             # noqa: E402


def cote(reglages) -> int:
    """Le côté qu'aurait une icône du journal avec ces réglages.

    La propriété se lit sur un faux objet : elle ne touche qu'aux réglages,
    et monter la fenêtre entière pour trois multiplications serait cher.
    """
    faux = types.SimpleNamespace(
        _settings=reglages,
        PART_ICONE_JOURNAL=MainWindow.PART_ICONE_JOURNAL)
    return MainWindow._cote_icone_journal.fget(faux)


class IconeDuJournal(unittest.TestCase):

    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self._vrai = config.config_dir
        config.config_dir = lambda: self._dossier.name

    def tearDown(self):
        config.config_dir = self._vrai
        self._dossier.cleanup()

    def test_a_la_taille_normale_c_est_la_hauteur_d_une_ligne(self):
        reglages = config.Settings()
        reglages.zoom = 1.0
        self.assertEqual(24, cote(reglages))

    def test_chaque_cran_donne_une_taille_differente(self):
        reglages = config.Settings()
        vues = []
        for cran in config.Settings.PALIERS_ZOOM:
            reglages.zoom = cran / 100
            vues.append(cote(reglages))
        # Le defaut d'origine : cette liste valait vingt-quatre sept fois.
        self.assertEqual(sorted(set(vues)), vues)

    def test_c_est_la_moitie_de_l_icone_d_inventaire(self):
        reglages = config.Settings()
        for cran in config.Settings.PALIERS_ZOOM:
            reglages.zoom = cran / 100
            with self.subTest(zoom=cran):
                self.assertEqual(round(reglages.icon_size / 2),
                                 cote(reglages))


if __name__ == "__main__":
    unittest.main()
