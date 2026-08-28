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


class PortraitDePersonnage(unittest.TestCase):
    """L'adresse du rendu, et le cache qui la suit.

    Le cadrage et l'équipement doivent être **les mêmes que sur le portage
    Android**, sans quoi le même personnage n'a pas le même visage d'une
    application à l'autre.
    """

    XML = (
        '<character><race>matis</race><gender>male</gender>'
        '<body><hairtype>88</hairtype><haircolor>4</haircolor><tattoo>0</tattoo>'
        '<eyescolor>3</eyescolor>'
        '<gabarit height="0" torso="8" arms="8" legs="7" breast="8"/>'
        '<morph target1="2" target2="4" target3="6" target4="2" target5="5"'
        ' target6="0" target7="6" target8="0"/></body>'
        '<equipment><headdress color="6">casque.sitem</headdress>'
        '<chest color="6">cuirasse.sitem</chest>'
        '<handr color="0">epee.sitem</handr>'
        '<feet color="">bottes.sitem</feet></equipment></character>'
    )

    def _url(self):
        import xml.etree.ElementTree as ET
        from zyroom.ryzom_api import _character_portrait_url
        return _character_portrait_url(ET.fromstring(self.XML))

    def test_le_cadrage_est_le_gros_plan(self):
        """Le corps entier montrait un personnage nu de la taille aux pieds :
        le service n'habille que les créneaux qu'on lui envoie."""
        self.assertIn("zoom=face", self._url())

    def test_toutes_les_pieces_portees_sont_envoyees(self):
        u = self._url()
        for attendu in ("head=casque.sitem/6", "chest=cuirasse.sitem/6",
                        "handr=epee.sitem/0"):
            self.assertIn(attendu, u)

    def test_une_couleur_absente_vaut_zero(self):
        self.assertIn("feet=bottes.sitem/0", self._url())

    def test_un_creneau_vide_n_est_pas_envoye(self):
        self.assertNotIn("legs=", self._url())

    def test_l_adresse_est_chiffree(self):
        self.assertTrue(self._url().startswith("https://"))

    def test_le_cache_suit_l_adresse(self):
        """Sinon changer le rendu ne change rien à l'écran : le fichier est
        déjà là, et il est servi tel quel."""
        import tempfile, os
        from unittest import mock
        from zyroom import config
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(config, "cache_dir", lambda: d):
                a = config.portrait_path("character", "1", "https://a")
                b = config.portrait_path("character", "1", "https://b")
                self.assertNotEqual(a, b)

    def test_l_ancien_portrait_est_ecarte(self):
        """Une tenue par fichier ferait grossir le cache sans fin."""
        import tempfile, os
        from unittest import mock
        from zyroom import config
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(config, "cache_dir", lambda: d):
                a = config.portrait_path("character", "1", "https://a")
                open(a, "wb").close()
                config.portrait_path("character", "1", "https://b")
                self.assertFalse(os.path.exists(a))



class NomsDeBetes(unittest.TestCase):
    """Le nom d'une bête, tel que le jeu l'écrit.

    Ryzom range les traductions dans une seule chaîne et écrit ses espaces
    insécables en UTF-8 relu comme du latin-1. Sans décodage, la liste des
    contenants afficherait `$#[wk]Xiom's Zig[fr]Zig de Xiom`.
    """

    def _nom(self, brut):
        from zyroom.ryzom_api import nom_multilingue
        return nom_multilingue(brut)

    def test_le_segment_francais_est_retenu(self):
        self.assertEqual(
            "Zig de Xiom",
            self._nom("$#[wk]Xiom'sÂ Zig[fr]ZigÂ deÂ Xiom"))

    def test_un_nom_simple_ne_bouge_pas(self):
        self.assertEqual("Mounty", self._nom("Mounty"))

    def test_le_dollar_de_fin_est_retire(self):
        self.assertEqual("Zig Yubo Premium",
                         self._nom("ZigÂ YuboÂ Premium$"))

    def test_un_accent_veritable_survit(self):
        """Un nom qui porte légitimement un « Â » ne doit pas être abîmé."""
        self.assertEqual("Bête à Â", self._nom("Bête à Â"))

    def test_sans_segment_francais_on_prend_le_premier(self):
        self.assertEqual("Zig", self._nom("$#[wk]Zig[de]Zig auf Deutsch"))

    def test_un_nom_vide_reste_vide(self):
        self.assertEqual("", self._nom(""))


class AccentsDuFlux(unittest.TestCase):
    """Les accents que l'API rend en UTF-8 relu comme du latin-1.

    Relevé sur la guilde Rod of Heaven : son coffre 2 s'appelle « Bijoux /
    Amplis et Légère », et le flux le livre `L&#xC3;&#xA9;g&#xC3;&#xA8;re`.
    Sans réparation, la liste des coffres affiche « LÃ©gÃ¨re ».
    """

    def _repare(self, brut):
        from zyroom.ryzom_api import repare_accents
        return repare_accents(brut)

    def test_le_nom_de_coffre_releve_est_repare(self):
        self.assertEqual("Bijoux / Amplis et Légère",
                         self._repare("Bijoux / Amplis et L\u00c3\u00a9g\u00c3\u00a8re"))

    def test_un_texte_sain_ne_bouge_pas(self):
        self.assertEqual("Tenterez-vous de percer son mystère.....",
                         self._repare("Tenterez-vous de percer son mystère....."))

    def test_l_ascii_traverse_intact(self):
        self.assertEqual("Mixed Mps", self._repare("Mixed Mps"))

    def test_le_coffre_de_guilde_arrive_repare(self):
        """Bout en bout : le nom lu dans <chests> passe par la réparation."""
        from zyroom.ryzom_api import parse_guild
        flux = (
            '<?xml version="1.0"?><ryzomapi version="1.0"><guild modules="G01">'
            '<gid>1</gid><name>Rod of Heaven</name><shard>atys</shard>'
            '<chests><chest><name>Mixed Mps</name><bulkmax>1000</bulkmax></chest>'
            '<chest><name>Bijoux / Amplis et L&#xC3;&#xA9;g&#xC3;&#xA8;re</name>'
            '<bulkmax>1000</bulkmax></chest></chests>'
            '</guild></ryzomapi>')
        ent = parse_guild(flux.encode("utf-8"), lambda sheet: sheet)
        self.assertEqual("Coffre 2 — Bijoux / Amplis et Légère",
                         ent.inventories[1].label)


if __name__ == "__main__":
    unittest.main()
