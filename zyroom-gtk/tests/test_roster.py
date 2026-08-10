"""Le registre du personnel : arrivées, départs, changements de grade."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import roster                                          # noqa: E402


class Grades(unittest.TestCase):

    def test_les_grades_se_disent_en_francais(self):
        self.assertEqual("Haut officier", roster.nom_grade("HighOfficer"))
        self.assertEqual("Chef", roster.nom_grade("Leader"))

    def test_un_grade_inconnu_reste_lisible(self):
        self.assertEqual("Bidule", roster.nom_grade("Bidule"))
        self.assertEqual("—", roster.nom_grade(""))

    def test_le_chef_se_classe_avant_les_membres(self):
        self.assertLess(roster.rang_grade("Leader"), roster.rang_grade("Member"))
        self.assertLess(roster.rang_grade("Officer"), roster.rang_grade("Member"))


class Mouvements(unittest.TestCase):

    def test_arrivee_depart_et_changement_de_grade(self):
        avant = {"Dale": "Member", "Nizy": "Officer", "Elanor": "Member"}
        apres = {"Dale": "Officer", "Elanor": "Member", "Kiranaa": "Member"}
        par_nom = {c.member: c for c in roster.diff(avant, apres)}
        self.assertEqual({"Dale", "Nizy", "Kiranaa"}, set(par_nom))
        self.assertEqual("grade", par_nom["Dale"].kind)
        self.assertTrue(par_nom["Dale"].promotion)
        self.assertEqual("depart", par_nom["Nizy"].kind)
        self.assertEqual("arrivee", par_nom["Kiranaa"].kind)

    def test_une_retrogradation_n_est_pas_une_promotion(self):
        c = roster.diff({"Dale": "Officer"}, {"Dale": "Member"})[0]
        self.assertEqual("grade", c.kind)
        self.assertFalse(c.promotion)

    def test_rien_ne_bouge_rien_ne_se_journalise(self):
        etat = {"Dale": "Member"}
        self.assertEqual([], roster.diff(etat, dict(etat)))

    def test_les_lignes_se_lisent_telles_quelles(self):
        arrivee, depart = roster.diff({}, {"Kiranaa": "Member"})[0], \
            roster.diff({"Nizy": "Officer"}, {})[0]
        self.assertIn("a rejoint la guilde", roster.decrire(arrivee))
        self.assertIn("a quitté la guilde", roster.decrire(depart))
        montee = roster.diff({"Dale": "Member"}, {"Dale": "Officer"})[0]
        # Le signe n'est plus dans le texte : l'écran le pose à part, en
        # couleur, et `promotion` dit lequel choisir.
        self.assertIn("Membre → Officier", roster.decrire(montee))
        self.assertTrue(montee.promotion)


class Journal(unittest.TestCase):

    def store(self, dossier):
        return roster.RosterStore(dossier, "105906237")

    def test_le_premier_releve_ne_journalise_rien(self):
        """Sinon les cent soixante-dix membres passeraient pour autant
        d'arrivées le jour de l'installation."""
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            self.assertTrue(s.jamais_releve())
            self.assertEqual([], s.record([("Dale", "Member"), ("Nizy", "Officer")]))
            self.assertFalse(s.jamais_releve())
            changements = s.record([("Dale", "Officer"), ("Kiranaa", "Member")])
            self.assertEqual({"Dale", "Nizy", "Kiranaa"},
                             {c.member for c in changements})
            self.assertEqual(3, len(s.history()))

    def test_un_releve_vide_ne_vide_pas_la_guilde(self):
        """L'API rend parfois une guilde sans son bloc de membres : la guilde
        entière semblerait alors avoir démissionné."""
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            s.record([("Dale", "Member"), ("Nizy", "Officer")])
            self.assertEqual([], s.record([]))
            self.assertEqual([], s.history())

    def test_le_journal_se_relit_du_plus_recent_au_plus_ancien(self):
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            s.record([("Dale", "Member")])
            s.record([("Dale", "Member"), ("Nizy", "Member")])
            s.record([("Dale", "Officer"), ("Nizy", "Member")])
            histoire = s.history()
            self.assertEqual(2, len(histoire))
            self.assertGreaterEqual(histoire[0].at, histoire[1].at)
            s.clear()
            self.assertEqual([], s.history())


if __name__ == "__main__":
    unittest.main()
