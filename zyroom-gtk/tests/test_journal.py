"""Le journal : les libellés de coffres, et la coupure entre deux journées.

Les coffres de guilde portent, après leur nom, ce que la guilde y range — et
l'API tronque le tout à une quarantaine de signes, si bien que la parenthèse ne
se referme presque jamais. « Coffre 15 — La Lune Des Maraudeurs(Gh Armure » est
le libellé réel, pas un exemple inventé : il vient du journal de Ludo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom.window import MainWindow                              # noqa: E402


class LibelleDeCoffre(unittest.TestCase):

    #: Relevés tels quels dans le journal de la guilde.
    RELEVES = (
        ("Coffre 15 — La Lune Des Maraudeurs(Gh Armure",
         "Coffre 15 — La Lune Des Maraudeurs"),
        ("Coffre 2 — La Resserre Lunaire 1/2 (Equipem",
         "Coffre 2 — La Resserre Lunaire 1/2"),
        ("Coffre 7 — La Forge Lunaire (Craft Armes 3/",
         "Coffre 7 — La Forge Lunaire"),
        ("Coffre 9 — La Lune d'Ambre(Craft Bijoux/Amp",
         "Coffre 9 — La Lune d'Ambre"),
    )

    def test_le_parenthetique_disparait(self):
        for brut, attendu in self.RELEVES:
            self.assertEqual(attendu, MainWindow._sans_parenthese(brut))

    def test_ce_qui_n_en_a_pas_ne_bouge_pas(self):
        for intact in ("Sac", "Coffre 1", "Appartement", "Zig 3",
                       "Coffre 4 — Gh Mps Utile pour les Coffres"):
            self.assertEqual(intact, MainWindow._sans_parenthese(intact))

    def test_un_libelle_entierement_parenthese_est_gardé(self):
        """Mieux vaut un libellé étrange que pas de libellé du tout.

        Si la troncature laissait une parenthèse en tête, couper rendrait une
        chaîne vide et la colonne serait muette : on garde alors l'original."""
        self.assertEqual("(Gh Armure", MainWindow._sans_parenthese("(Gh Armure"))
        self.assertEqual("", MainWindow._sans_parenthese(""))


if __name__ == "__main__":
    unittest.main()
