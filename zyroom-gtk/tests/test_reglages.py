"""Les réglages qui survivent à la fermeture.

La taille des fenêtres — la principale, celle des alertes — est enregistrée
à la fermeture et relue au lancement.
Ce qu'on protège ici, c'est le cas où le fichier ment : un réglage recopié
d'une autre machine, un écran débranché depuis, une valeur bricolée à la main.
Une fenêtre de trois pixels de haut ne se rattrape pas à la souris.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import config                                        # noqa: E402


class Fenetre(unittest.TestCase):

    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self._vrai = config.config_dir
        config.config_dir = lambda: self._dossier.name

    def tearDown(self):
        config.config_dir = self._vrai
        self._dossier.cleanup()

    def test_sans_reglage_la_taille_est_celle_du_defaut(self):
        self.assertEqual(config.Settings.FENETRE_DEFAUT,
                         config.Settings().window_size)
        self.assertFalse(config.Settings().window_maximized)

    def test_la_taille_survit_a_la_fermeture(self):
        reglages = config.Settings()
        reglages.window_size = (1280, 800)
        reglages.window_maximized = True
        relu = config.Settings()
        self.assertEqual((1280, 800), relu.window_size)
        self.assertTrue(relu.window_maximized)

    def test_une_taille_aberrante_revient_au_defaut(self):
        for taille in ((10, 10), (0, 0), (3, 700), (1024, 12),
                       (99999, 700), (1024, 99999), (-100, -100)):
            reglages = config.Settings()
            reglages.window_size = taille
            self.assertEqual(config.Settings.FENETRE_DEFAUT,
                             config.Settings().window_size,
                             f"{taille} aurait dû être refusée")

    def test_une_taille_juste_est_gardee(self):
        for taille in ((360, 300), (960, 680), (3840, 2160)):
            reglages = config.Settings()
            reglages.window_size = taille
            self.assertEqual(taille, config.Settings().window_size)

    def test_sans_reglage_les_alertes_prennent_leur_defaut(self):
        self.assertEqual(config.Settings.ALERTES_DEFAUT,
                         config.Settings().alerts_window_size)

    def test_la_taille_des_alertes_survit_a_la_fermeture(self):
        reglages = config.Settings()
        reglages.alerts_window_size = (820, 600)
        self.assertEqual((820, 600), config.Settings().alerts_window_size)

    def test_les_deux_fenetres_ont_chacune_leur_taille(self):
        """Élargir les alertes ne doit pas élargir la fenêtre principale."""
        reglages = config.Settings()
        reglages.window_size = (1280, 800)
        reglages.alerts_window_size = (820, 600)
        relu = config.Settings()
        self.assertEqual((1280, 800), relu.window_size)
        self.assertEqual((820, 600), relu.alerts_window_size)

    def test_une_taille_d_alertes_aberrante_revient_au_defaut(self):
        for taille in ((10, 10), (0, 0), (3, 700), (99999, 700), (-100, -100)):
            reglages = config.Settings()
            reglages.alerts_window_size = taille
            self.assertEqual(config.Settings.ALERTES_DEFAUT,
                             config.Settings().alerts_window_size,
                             f"{taille} aurait dû être refusée")

    def test_un_fichier_illisible_ne_fait_pas_tomber_le_lancement(self):
        """Une valeur qui n'est pas un nombre : on repart du défaut.

        Ce réglage est lu **avant** que la fenêtre existe : une exception ici
        empêcherait l'application de démarrer, et il n'y aurait plus d'écran
        pour le dire.
        """
        chemin = os.path.join(self._dossier.name, "settings.ini")
        with open(chemin, "w", encoding="utf-8") as fh:
            fh.write("[GENERAL]\nWindowWidth = grand\nWindowHeight = 700\n"
                     "WindowMaximized = peut-être\n")
        self.assertEqual(config.Settings.FENETRE_DEFAUT,
                         config.Settings().window_size)
        self.assertFalse(config.Settings().window_maximized)


if __name__ == "__main__":
    unittest.main()
