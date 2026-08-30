"""Les gouttes de spécialité : quelles couleurs, pour quels bonus.

Le placement se juge à l'œil ; ce qui se teste, c'est la correspondance entre
un bonus et sa goutte, et le fait qu'un item sans bonus n'ajoute aucun widget
à une grille qui en compte déjà des centaines.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")

from zyroom import specialites
from zyroom.models import ItemInfo


class Gouttes(unittest.TestCase):

    def test_un_item_sans_bonus_n_a_pas_de_goutte(self):
        """Une matière, une graine : rien à dessiner, et donc aucun widget."""
        self.assertEqual([], specialites.bonus(ItemInfo(sheet="m0067.sitem")))
        self.assertIsNone(specialites.bandeau(ItemInfo(sheet="m0067.sitem")))
        self.assertEqual("", specialites.resume(ItemInfo(sheet="m0067.sitem")))

    def test_chaque_jauge_a_sa_specialite(self):
        """Vie, magie, combat, forage : les quatre jauges du jeu, dans l'ordre."""
        item = ItemInfo(sheet="ic.sitem", hp_buff=12, sap_buff=8,
                        sta_buff=5, focus_buff=3)
        self.assertEqual(["Vie", "Magie", "Combat", "Forage"],
                         [libelle for libelle, _v, _c in specialites.bonus(item)])
        self.assertEqual([12, 8, 5, 3],
                         [valeur for _l, valeur, _c in specialites.bonus(item)])

    def test_seuls_les_bonus_presents_comptent(self):
        """Un item monté en sève ne porte que la goutte verte."""
        item = ItemInfo(sheet="ic.sitem", sap_buff=15)
        self.assertEqual([("Magie", 15, "#4caf50")], specialites.bonus(item))
        self.assertEqual("Magie +15", specialites.resume(item))

    def test_l_infobulle_nomme_ce_que_la_couleur_montre(self):
        item = ItemInfo(sheet="ic.sitem", hp_buff=12, sta_buff=5)
        self.assertEqual("Vie +12, Combat +5", specialites.resume(item))

    def test_l_icone_ne_porte_que_la_goutte_dominante(self):
        """Trois bonus, une seule goutte : la plus grosse, comme dans le jeu."""
        item = ItemInfo(sheet="ic.sitem", hp_buff=40, sap_buff=125, sta_buff=20)
        self.assertEqual(("Magie", 125, "#4caf50"), specialites.principal(item))
        # mais l'infobulle, elle, les montre toutes
        self.assertEqual(3, len(specialites.bonus(item)))

    def test_pas_de_goutte_dominante_sans_bonus(self):
        self.assertIsNone(specialites.principal(ItemInfo(sheet="m0067.sitem")))

    def test_les_gouttes_ne_prennent_pas_le_clic(self):
        """Le clic droit et le double-clic vont a l'icone, pas au dessin."""
        bandeau = specialites.bandeau(ItemInfo(sheet="ic.sitem", hp_buff=1))
        self.assertIsNotNone(bandeau)
        self.assertFalse(bandeau.get_can_target())


if __name__ == "__main__":
    unittest.main()
