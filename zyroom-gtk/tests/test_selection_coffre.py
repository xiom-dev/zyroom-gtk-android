"""Le coffre qu'on regarde ne doit pas changer tout seul.

Le cas réel : la relève automatique passe toutes les quinze minutes et rebâtit
la liste des contenants. Elle ramenait au premier — on consultait le coffre
onze de la Lune Éternelle, on regardait ailleurs, et l'on retrouvait le coffre
un sans avoir rien demandé.
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom.window import MainWindow                              # noqa: E402


def entite(kind="guild", ident="105906237", cles=("chest1", "chest2", "chest11")):
    """Une entité réduite à ce que la méthode regarde."""
    return types.SimpleNamespace(
        kind=kind, entity_id=ident,
        inventories=[types.SimpleNamespace(key=cle) for cle in cles])


def fenetre(courant):
    """Une fenêtre réduite au souvenir du contenant affiché."""
    return types.SimpleNamespace(_inv_courant=courant)


class RetrouverLeCoffre(unittest.TestCase):

    def test_le_coffre_affiché_est_retrouvé(self):
        rang = MainWindow._rang_du_contenant(
            fenetre((("guild", "105906237"), "chest11")), entite())
        self.assertEqual(2, rang)

    def test_sans_souvenir_on_part_du_premier(self):
        self.assertEqual(0, MainWindow._rang_du_contenant(fenetre(None), entite()))

    def test_changer_d_entité_repart_du_premier(self):
        """Les coffres d'une guilde n'ont rien à voir avec le sac d'un perso."""
        rang = MainWindow._rang_du_contenant(
            fenetre((("character", "689325"), "bag")), entite())
        self.assertEqual(0, rang)

    def test_un_coffre_disparu_ramène_au_premier(self):
        """L'API peut en rendre un de moins : mieux vaut le premier qu'un vide."""
        rang = MainWindow._rang_du_contenant(
            fenetre((("guild", "105906237"), "chest18")), entite())
        self.assertEqual(0, rang)

    def test_le_repère_est_la_clé_et_non_le_rang(self):
        """Un coffre inséré avant le nôtre ne doit pas décaler l'affichage."""
        rang = MainWindow._rang_du_contenant(
            fenetre((("guild", "105906237"), "chest11")),
            entite(cles=("chest0", "chest1", "chest2", "chest11")))
        self.assertEqual(3, rang)


if __name__ == "__main__":
    unittest.main()
