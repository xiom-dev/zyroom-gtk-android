"""L'enchantement d'un objet : ce que le flux en dit, et ce qu'on en montre.

Le cas réel derrière ce fichier : le flux **personnage** porte un nœud
`<enchantment>` avec les briques du sort, le flux **guilde** n'en porte aucun.
La distinction n'est pas une supposition, elle est vérifiée ici sur des extraits
des deux flux — c'est elle qui explique qu'un coffre de guilde ne montre jamais
d'icône de sort.
"""

import os
import sys
import unittest
from xml.etree.ElementTree import fromstring

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import enchantements
from zyroom.models import ItemInfo, parse_item

# Un objet du flux personnage : sort, charges, coût.
PERSONNAGE = """
<item id="7305822097628491425" slot="4"><stack>1</stack>
  <sheet>icmm2ms_3.sitem</sheet><quality>250</quality><locked>1</locked>
  <hp>136</hp><sapload>1719</sapload>
  <enchantment cost="-225">
    <sbrick>bmpa01.sbrick</sbrick>
    <sbrick>bmoetea04.sbrick</sbrick>
    <sbrick>bmoetme00225.sbrick</sbrick>
    <sbrick>bmca00065.sbrick</sbrick>
  </enchantment>
</item>"""

# Le même genre d'objet vu depuis un coffre de guilde : rien sur le sort.
GUILDE = """
<item id="7288895506647062706" slot="6542"><stack>1</stack>
  <sheet>icokamm1sa_1.sitem</sheet><quality>250</quality><locked>0</locked>
  <hp>113</hp>
  <craftparameters><durability value="154">0.53</durability>
    <sapload value="1769">0.70</sapload><hpbuff>125</hpbuff></craftparameters>
</item>"""

#: Ce que rend le pack du client pour ces briques.
NOMS = {
    "bmpa01.sbrick": "Missile Atysien",
    "bmoetea04.sbrick": "Dégât d'Electricité ",
    "bmoetme00225.sbrick": "Dégât d'Electricité 5",
    "bmca00065.sbrick": "Crédit Sève 14",
}


def nommer(sheet):
    return NOMS.get(sheet, sheet)


class FluxPersonnage(unittest.TestCase):

    def setUp(self):
        self.item = parse_item(fromstring(PERSONNAGE))

    def test_le_sort_est_lu(self):
        self.assertTrue(enchantements.enchante(self.item))
        self.assertEqual(4, len(self.item.enchant_bricks))
        self.assertEqual(-225, self.item.enchant_cost)
        self.assertEqual(1719, self.item.sap_charges)

    def test_l_icone_est_celle_de_l_action(self):
        """La première brique — le missile —, comme dans le jeu."""
        self.assertEqual("bmpa01.sbrick", enchantements.brique_icone(self.item))

    def test_le_resume_ecarte_les_credits(self):
        """« Crédit Sève 14 » dit le coût, pas ce que le sort fait."""
        self.assertEqual("Missile Atysien · Dégât d'Electricité 5",
                         enchantements.resume(self.item, nommer))

    def test_le_resume_garde_la_brique_la_plus_precise(self):
        """Deux briques pour un effet : celle qui porte le niveau l'emporte."""
        resume = enchantements.resume(self.item, nommer)
        self.assertIn("Dégât d'Electricité 5", resume)
        self.assertNotIn("Electricité ·", resume)

    def test_sans_pack_on_voit_au_moins_qu_il_y_a_un_sort(self):
        brut = enchantements.resume(self.item, lambda sheet: sheet)
        self.assertIn("bmpa01.sbrick", brut)


class FluxGuilde(unittest.TestCase):

    def test_un_coffre_de_guilde_ne_dit_rien_du_sort(self):
        """L'API ne transmet pas l'enchantement des coffres — rien à montrer."""
        item = parse_item(fromstring(GUILDE))
        self.assertFalse(enchantements.enchante(item))
        self.assertEqual("", enchantements.brique_icone(item))
        self.assertEqual("", enchantements.resume(item, nommer))

    def test_le_sapload_de_craft_n_est_pas_une_charge(self):
        """Celui de `craftparameters` est la capacité, pas ce qui reste."""
        item = parse_item(fromstring(GUILDE))
        self.assertEqual(0, item.sap_charges)
        self.assertFalse(item.sap)


class SansEnchantement(unittest.TestCase):

    def test_un_item_nu(self):
        item = ItemInfo(sheet="m0067.sitem")
        self.assertFalse(enchantements.enchante(item))
        self.assertEqual("", enchantements.resume(item, nommer))


if __name__ == "__main__":
    unittest.main()
