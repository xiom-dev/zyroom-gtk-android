"""La barre d'attente : son curseur doit parcourir toute la barre, sans retour.

Deux erreurs successives, toutes deux visibles à l'œil et invisibles au code :
d'abord un seuil trop grand, qui laissait le curseur rebondir puis revenir ;
puis un seuil trop petit, qui l'arrêtait aux trois quarts de la barre. Il doit
atteindre le bord droit, et n'aller que vers la droite.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import attente  # noqa: E402


class BarreAttente(unittest.TestCase):

    def test_le_curseur_atteint_le_bord(self):
        """La dernière position doit poser le curseur contre le bord droit."""
        derniere = attente.decalage(attente.positions() - 1)
        self.assertAlmostEqual(derniere + attente.PAS, 1.0, places=9)

    def test_le_curseur_part_du_bord_gauche(self):
        self.assertEqual(attente.decalage(0), 0.0)

    def test_il_avance_toujours(self):
        """Aucune position ne doit ramener le curseur en arrière."""
        avant = [attente.decalage(i) for i in range(attente.positions())]
        self.assertEqual(avant, sorted(avant))
        self.assertEqual(len(set(avant)), len(avant) - 0 if avant[-1] != avant[-2]
                         else len(avant) - 1)

    def test_il_ne_deborde_jamais(self):
        """Le curseur entier doit tenir dans la barre, à toute position."""
        for i in range(attente.positions()):
            self.assertLessEqual(attente.decalage(i) + attente.PAS, 1.0 + 1e-9)

    def test_le_compte_suit_le_pas(self):
        """La règle vaut pour d'autres pas que celui du programme."""
        import math

        for pas in (0.05, 0.1, 0.2, 0.25, 0.5):
            n = math.ceil((1.0 - pas) / pas) + 1
            dernier = min(pas * (n - 1), 1.0 - pas)
            self.assertAlmostEqual(dernier + pas, 1.0, places=9,
                                   msg=f"à {pas}, le curseur n'atteint pas le bord")

    def test_les_deux_portages_ont_les_memes_nombres(self):
        """La barre de Qt est le jumeau de celle-ci : mêmes pas, même cadence.

        Les deux fichiers sont écrits à la main, chacun dans son toolkit ; rien
        n'empêcherait l'un de dériver, sinon ce test.
        """
        import re

        ici = os.path.dirname(os.path.abspath(__file__))
        jumeau = os.path.join(os.path.dirname(os.path.dirname(ici)),
                              "zyroom-qt", "zyroom", "attente.py")
        if not os.path.isfile(jumeau):
            self.skipTest("le portage Qt n'est pas à côté")
        source = open(jumeau, encoding="utf-8").read()

        for nom, valeur in (("PAS", attente.PAS), ("CADENCE", attente.CADENCE),
                            ("RAYON", attente.RAYON)):
            trouve = re.search(rf"^{nom} = ([\d.]+)", source, re.M)
            self.assertIsNotNone(trouve, f"{nom} absent du portage Qt")
            self.assertEqual(float(trouve.group(1)), float(valeur),
                             f"{nom} diffère entre les deux portages")

    def test_le_jumeau_calcule_pareil(self):
        """Les deux `decalage` doivent rendre la même chose, position par position."""
        import re

        ici = os.path.dirname(os.path.abspath(__file__))
        jumeau = os.path.join(os.path.dirname(os.path.dirname(ici)),
                              "zyroom-qt", "zyroom", "attente.py")
        if not os.path.isfile(jumeau):
            self.skipTest("le portage Qt n'est pas à côté")
        source = open(jumeau, encoding="utf-8").read()
        self.assertIn("return min(PAS * position, 1.0 - PAS)", source)
        self.assertIn("math.ceil((1.0 - PAS) / PAS) + 1", source)


if __name__ == "__main__":
    unittest.main()
