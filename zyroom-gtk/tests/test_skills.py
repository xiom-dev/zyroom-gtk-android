"""L'arbre des compétences, déduit des codes.

Mêmes cas que côté Android, où cette logique est née : le repli, lui, ne se
vérifie qu'à l'œil, mais tout ce qui décide *quoi* afficher se teste ici.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom.skills import (Skill, branch_level, build_tree, parse_level,  # noqa: E402
                           visible)

FLUX = os.path.expanduser("~/.cache/zyroom-gtk/character/689325.xml")


def arbre(*codes):
    return build_tree([Skill(code=c, level=100) for c in codes])


class Niveaux(unittest.TestCase):

    def test_le_decimal_est_un_avancement(self):
        """« 164.52 » : niveau 164, et 52 % du suivant."""
        self.assertEqual((164, 52), parse_level("164.52"))
        # 0,06 flottant ne vaut pas exactement 6 : c'est l'arrondi qui répond.
        self.assertEqual((101, 6), parse_level("101.06"))

    def test_un_entier_ne_dit_rien_de_l_avancement(self):
        self.assertEqual((250, 0), parse_level("250"))

    def test_une_valeur_illisible_ne_fait_pas_tomber_la_lecture(self):
        self.assertEqual((0, 0), parse_level(""))
        self.assertEqual((0, 0), parse_level("nawak"))


class Hierarchie(unittest.TestCase):

    def test_elle_se_deduit_des_prefixes(self):
        noeuds = {n.skill.code: n for n in arbre("sf", "sfm", "sfms", "sfr")}
        self.assertIsNone(noeuds["sf"].parent)
        self.assertEqual(0, noeuds["sf"].depth)
        self.assertTrue(noeuds["sf"].has_children)
        self.assertEqual("sfm", noeuds["sfms"].parent)
        self.assertEqual(2, noeuds["sfms"].depth)
        self.assertFalse(noeuds["sfms"].has_children)
        self.assertTrue(all(n.root == "sf" for n in noeuds.values()))

    def test_un_echelon_manquant_ne_decale_pas_l_affichage(self):
        """Si l'API saute un échelon — sfm absent alors que sfms existe —, sfms
        se rattache à sf et non deux crans trop à droite."""
        noeuds = {n.skill.code: n for n in arbre("sf", "sfms")}
        self.assertEqual("sf", noeuds["sfms"].parent)
        self.assertEqual(1, noeuds["sfms"].depth)


class Repli(unittest.TestCase):

    def test_tout_est_replie_au_depart(self):
        self.assertEqual(["sc", "sf"],
                         [n.skill.code for n in visible(arbre("sf", "sfm", "sc"), set())])

    def test_ouvrir_ne_montre_que_les_enfants_directs(self):
        a = arbre("sf", "sfm", "sfms", "sfmd", "sfr")
        self.assertEqual(["sf", "sfm", "sfr"],
                         [n.skill.code for n in visible(a, {"sf"})])
        self.assertEqual(["sf", "sfm", "sfmd", "sfms", "sfr"],
                         [n.skill.code for n in visible(a, {"sf", "sfm"})])

    def test_replier_un_parent_cache_les_petits_enfants(self):
        """Sans perdre leur état : rouvrir retrouve ce qu'on avait laissé."""
        a = arbre("sf", "sfm", "sfms")
        ouverts = {"sf", "sfm"}
        self.assertEqual(3, len(visible(a, ouverts)))
        self.assertEqual(["sf"], [n.skill.code for n in visible(a, ouverts - {"sf"})])
        self.assertEqual(3, len(visible(a, ouverts)))


class SurLeVraiFlux(unittest.TestCase):
    """Le flux du personnage mis en cache, quand il est là."""

    @unittest.skipUnless(os.path.isfile(FLUX), "aucun flux en cache")
    def test_quatre_racines_et_rien_d_autre_au_depart(self):
        from zyroom import ryzom_api
        with open(FLUX, "rb") as fh:
            ent = ryzom_api.parse_character(fh.read())
        a = build_tree(ent.skills)
        self.assertGreater(len(a), 150)
        racines = visible(a, set())
        self.assertEqual(["sc", "sf", "sh", "sm"],
                         sorted(n.skill.code for n in racines))
        self.assertTrue(all(n.has_children for n in racines))
        # Le niveau d'une racine plafonne bas : c'est le plus haut de ses
        # descendants qui dit où en est la branche.
        self.assertEqual(20, next(n for n in a if n.skill.code == "sf").skill.level)
        self.assertEqual(250, branch_level(a, "sf"))
        # Ouvrir l'artisanat ne déverse pas ses cent sept descendants.
        self.assertLess(len(visible(a, {"sc"})), 12)
        # Tout ouvrir rend l'arbre entier, sans perte ni doublon.
        self.assertEqual(len(a), len(visible(a, {n.skill.code for n in a})))

    @unittest.skipUnless(os.path.isfile(FLUX), "aucun flux en cache")
    def test_l_avancement_existe_et_reste_dans_ses_bornes(self):
        from zyroom import ryzom_api
        with open(FLUX, "rb") as fh:
            ent = ryzom_api.parse_character(fh.read())
        en_cours = [s for s in ent.skills if s.progress]
        self.assertTrue(en_cours, "aucune compétence en cours")
        self.assertTrue(all(1 <= s.progress <= 99 for s in en_cours))


if __name__ == "__main__":
    unittest.main()
