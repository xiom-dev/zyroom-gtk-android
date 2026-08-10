"""Les avant-postes : lecture de l'annuaire, et journal des prises."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import outposts                                        # noqa: E402

ANNUAIRE = b"""<?xml version="1.0"?>
<ryzomapi>
  <guild><name>La Lune Eternelle</name><icon>1377</icon>
    <outposts><outpost>fyros_outpost_04</outpost>
              <outpost>matis_outpost_03</outpost></outposts></guild>
  <guild><name>Purple Sap</name><icon>42</icon>
    <outposts><outpost>fyros_outpost_09</outpost></outposts></guild>
  <guild><name></name><icon>7</icon>
    <outposts><outpost>zorai_outpost_01</outpost></outposts></guild>
</ryzomapi>"""


class Lecture(unittest.TestCase):

    def test_l_annuaire_rend_les_avant_postes_tenus(self):
        liste = outposts.parse_outposts(ANNUAIRE)
        self.assertEqual(3, len(liste))
        self.assertEqual({"La Lune Eternelle", "Purple Sap"},
                         {o.guild for o in liste})

    def test_une_guilde_sans_nom_est_ecartee(self):
        """Le flux en contient, vestiges de guildes dissoutes."""
        self.assertNotIn("zorai_outpost_01",
                         [o.code for o in outposts.parse_outposts(ANNUAIRE)])

    def test_le_peuple_se_lit_dans_le_code(self):
        liste = {o.code: o for o in outposts.parse_outposts(ANNUAIRE)}
        self.assertEqual("fyros", liste["fyros_outpost_04"].people)
        self.assertEqual("fyros_outpost_04.outpost", liste["fyros_outpost_04"].name_key)

    def test_le_niveau_vient_de_la_table_figee(self):
        liste = {o.code: o for o in outposts.parse_outposts(ANNUAIRE)}
        self.assertEqual(200, liste["fyros_outpost_04"].level)
        self.assertEqual(150, liste["fyros_outpost_09"].level)

    def test_un_code_inconnu_n_invente_pas_de_niveau(self):
        self.assertEqual(0, outposts.Outpost("#15", "In Vino Veritas").level)


class Journal(unittest.TestCase):

    def test_une_prise_un_abandon_un_echange(self):
        avant = {"a": "Alpha", "b": "Beta", "c": "Gamma"}
        apres = {"a": "Alpha", "b": "Delta", "d": "Epsilon"}
        par_code = {c.outpost: c for c in outposts.diff(avant, apres)}
        self.assertEqual({"b", "c", "d"}, set(par_code))
        self.assertTrue(par_code["d"].taken)     # n'appartenait à personne
        self.assertTrue(par_code["c"].lost)      # rendu à personne
        self.assertEqual(("Beta", "Delta"), (par_code["b"].frm, par_code["b"].to))

    def test_rien_ne_bouge_rien_ne_se_journalise(self):
        etat = {"a": "Alpha"}
        self.assertEqual([], outposts.diff(etat, dict(etat)))

    def test_le_premier_releve_ne_journalise_rien(self):
        """Sinon les vingt-neuf avant-postes passeraient pour autant de prises
        le jour de l'installation."""
        with tempfile.TemporaryDirectory() as dossier:
            store = outposts.OutpostStore(dossier)
            self.assertTrue(store.jamais_releve())
            carte = outposts.parse_outposts(ANNUAIRE)
            self.assertEqual([], store.record(carte))
            self.assertFalse(store.jamais_releve())
            # Le deuxième, lui, compare.
            perdu = [o for o in carte if o.code != "matis_outpost_03"]
            changements = store.record(perdu)
            self.assertEqual(["matis_outpost_03"], [c.outpost for c in changements])
            self.assertTrue(changements[0].lost)
            self.assertEqual(1, len(store.history()))

    def test_le_journal_se_relit_du_plus_recent_au_plus_ancien(self):
        with tempfile.TemporaryDirectory() as dossier:
            store = outposts.OutpostStore(dossier)
            store.record(outposts.parse_outposts(ANNUAIRE))
            store.record([])                       # tout est perdu
            histoire = store.history()
            self.assertEqual(3, len(histoire))
            self.assertTrue(all(c.lost for c in histoire))
            store.clear()
            self.assertEqual([], store.history())


if __name__ == "__main__":
    unittest.main()
