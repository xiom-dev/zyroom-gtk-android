"""La forme d'une clé d'API, contrôlée avant de partir sur le réseau.

Le même contrôle existe sur le téléphone (`RyzomApi.isApiKey`), et il vaut la
peine des deux côtés : sans lui, une clé tronquée au copier-coller part quand
même, et l'on attend la réponse de Ryzom pour apprendre ce qui se voyait à
l'œil.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import ryzom_api                                     # noqa: E402


class FormeDeLaCle(unittest.TestCase):

    def test_une_vraie_cle_est_acceptee(self):
        # Deux clés de la forme attendue : 41 signes alphanumériques, « c »
        # pour un personnage, « g » pour une guilde.
        self.assertTrue(ryzom_api.is_api_key("c" + "0123456789abcdef" * 2 + "01234567"))
        self.assertTrue(ryzom_api.is_api_key("g" + "0123456789abcdef" * 2 + "01234567"))

    def test_une_cle_tronquee_est_refusee(self):
        entiere = "c" + "0123456789abcdef" * 2 + "01234567"
        self.assertEqual(41, len(entiere))
        self.assertFalse(ryzom_api.is_api_key(entiere[:-1]))
        self.assertFalse(ryzom_api.is_api_key(entiere + "0"))

    def test_une_cle_qui_ne_commence_ni_par_c_ni_par_g_est_refusee(self):
        self.assertFalse(ryzom_api.is_api_key("x" + "0123456789abcdef" * 2 + "01234567"))

    def test_ce_qui_n_est_pas_alphanumerique_est_refuse(self):
        # Un retour à la ligne collé avec la clé, un tiret, une espace.
        self.assertFalse(ryzom_api.is_api_key("c" + "-" * 40))
        self.assertFalse(ryzom_api.is_api_key(""))
        self.assertFalse(ryzom_api.is_api_key("c" + " " * 40))

    def test_l_adresse_de_la_page_est_celle_du_telephone(self):
        """Les deux applications envoient au même endroit."""
        self.assertEqual("https://app.ryzom.com/app_ryzomapi",
                         ryzom_api.KEY_PAGE)


if __name__ == "__main__":
    unittest.main()
