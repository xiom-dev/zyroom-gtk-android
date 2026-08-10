"""Le classement des objets pour l'affichage.

Les fiches et les noms employés ici sont relevés sur un vrai personnage : c'est
ce que le jeu écrit, y compris ses inconstances de casse.
"""

import unittest

from zyroom import sorting
from zyroom.models import ItemInfo, ItemType


def item(sheet: str, quality: int = 250, item_type=ItemType.EQUIPMENT) -> ItemInfo:
    it = ItemInfo()
    it.sheet = sheet
    it.quality = quality
    it.item_type = item_type
    return it


def _norm(text: str) -> str:
    """Ce que la fenêtre passe à `sort_key` : minuscule et sans accents."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


class OutfitKeyTest(unittest.TestCase):

    def test_armure_et_bijou_reconnus(self):
        self.assertEqual("icmah_3", sorting.outfit_key(item("icmahb_3.sitem")))
        self.assertEqual("iczj", sorting.outfit_key(item("iczja.sitem")))
        self.assertEqual("iczj_3", sorting.outfit_key(item("iczjr_3.sitem")))

    def test_une_arme_n_est_pas_une_piece_de_tenue(self):
        self.assertIsNone(sorting.outfit_key(item("iccm2pp.sitem")))
        self.assertIsNone(sorting.outfit_key(item("icokamm2ss_2.sitem")))
        self.assertIsNone(sorting.outfit_key(item("m0117dxajd01.sitem")))


class SortKeyTest(unittest.TestCase):

    def _range(self, noms: dict) -> list:
        objets = [item(sheet) for sheet in noms]
        objets.sort(key=lambda it: sorting.sort_key(it, _norm(noms[it.sheet])))
        return [noms[it.sheet] for it in objets]

    def test_les_pieces_d_une_tenue_se_lisent_de_la_tete_aux_pieds(self):
        # Deux tenues matis, l'une lourde l'autre légère : leurs noms les
        # entremêlaient — bottes avec bottes, gilets avec gilets.
        noms = {
            "icmahb_3.sitem": "Bottes Kara Paroks",
            "icmahh_3.sitem": "Casque Kara Parok",
            "icmahv_3.sitem": "Gilet Kara Parok",
            "icmalb_3.sitem": "Bottes Kara Wivas",
            "icmalv_3.sitem": "Gilet Kara Wiva",
        }
        self.assertEqual(
            ["Casque Kara Parok", "Gilet Kara Parok", "Bottes Kara Paroks",
             "Gilet Kara Wiva", "Bottes Kara Wivas"],
            self._range(noms))

    def test_les_bijoux_d_une_parure_restent_ensemble_malgre_la_casse(self):
        noms = {
            "iczjb.sitem": "bracelet zoraï",
            "iczjr.sitem": "Bague zoraï",
            "iczjd.sitem": "diadème zoraï",
        }
        self.assertEqual(["diadème zoraï", "Bague zoraï", "bracelet zoraï"],
                         self._range(noms))

    def test_les_matieres_restent_reunies_par_matiere(self):
        objets = [
            item("m0117dxajd01.sitem", 250, ItemType.NATURAL_MAT),
            item("m0101dxajd01.sitem", 100, ItemType.NATURAL_MAT),
            item("m0117dxafe01.sitem", 100, ItemType.NATURAL_MAT),
        ]
        objets.sort(key=lambda it: sorting.sort_key(it, it.sheet))
        self.assertEqual(
            ["m0101dxajd01.sitem", "m0117dxafe01.sitem", "m0117dxajd01.sitem"],
            [it.sheet for it in objets])

    def test_les_armes_ne_s_intercalent_pas_entre_deux_parures(self):
        # Le défaut de la première correction : le nom d'une arme se comparait
        # à un code de fiche, si bien que la Pique tombait au milieu des bijoux
        # zoraï. Les ensembles d'abord, le reste ensuite.
        noms = {
            "iccm2pp.sitem": "Pique",
            "icfm1bs_3.sitem": "Bâton Talusyx",
            "icmahb_3.sitem": "Bottes Kara Paroks",
            "iczja.sitem": "Anneau de cheville zoraï",
        }
        self.assertEqual(
            ["Bottes Kara Paroks", "Anneau de cheville zoraï",
             "Bâton Talusyx", "Pique"],
            self._range(noms))


if __name__ == "__main__":
    unittest.main()
