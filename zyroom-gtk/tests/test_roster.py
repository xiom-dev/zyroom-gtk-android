"""Le registre du personnel : arrivées, départs, changements de grade."""

import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import roster                                          # noqa: E402


class Grades(unittest.TestCase):

    def test_les_grades_se_disent_en_francais(self):
        self.assertEqual("Officier supérieur", roster.nom_grade("HighOfficer"))
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


class DateEntree(unittest.TestCase):
    """Le `<joined>` de l'API, ramené à un temps Unix."""

    # Liloulove, entrée dans La Lune Eternelle le 17 août 2026 vers 18 h —
    # alors que le journal, bâti sur les seuls relevés, la datait du 19.
    LILOULOVE = 8784019565

    def test_une_entree_connue_retombe_sur_son_jour(self):
        quand = roster.date_entree(self.LILOULOVE)
        self.assertEqual("2026-08-17",
                         time.strftime("%Y-%m-%d", time.localtime(quand)))

    def test_dix_pas_par_seconde(self):
        self.assertEqual(1, roster.date_entree(self.LILOULOVE + 10)
                         - roster.date_entree(self.LILOULOVE))

    def test_une_date_absurde_ne_vaut_rien(self):
        """Champ absent, compteur remis à zéro, horloge locale fausse : mieux
        vaut zéro — l'appelant retombera sur la date du relevé."""
        self.assertEqual(0, roster.date_entree(0))
        self.assertEqual(0, roster.date_entree(""))
        self.assertEqual(0, roster.date_entree(None))
        self.assertEqual(0, roster.date_entree(10 ** 12))       # dans l'avenir

    def test_l_arrivee_porte_la_date_de_l_api(self):
        c = roster.diff({}, {"Liloulove": "Member"},
                        {"Liloulove": roster.date_entree(self.LILOULOVE)})[0]
        self.assertEqual(roster.date_entree(self.LILOULOVE), c.at)

    def test_le_depart_et_le_grade_gardent_celle_du_releve(self):
        """De ceux-là, l'API ne dit rien : ni quand ils sont partis, ni quand
        ils ont changé de grade."""
        maintenant = int(time.time())
        for c in roster.diff({"Nizy": "Officer", "Dale": "Member"},
                             {"Dale": "Officer"},
                             {"Dale": roster.date_entree(self.LILOULOVE)}):
            self.assertAlmostEqual(maintenant, c.at, delta=5)

    def test_une_arrivee_ne_se_date_jamais_de_l_avenir(self):
        """Une horloge locale en retard la poserait en tête du journal."""
        avenir = int(time.time()) + 30 * 86400
        c = roster.diff({}, {"Kiranaa": "Member"}, {"Kiranaa": avenir})[0]
        self.assertLessEqual(c.at, int(time.time()))

    def test_l_arrivee_ne_precede_pas_le_releve_precedent(self):
        """Le compteur de l'API dérive ; la fenêtre des deux relevés, non. Un
        nouveau venu est forcément entré après le relevé qui ne le voyait pas
        encore."""
        veille = int(time.time()) - 86400
        c = roster.diff({}, {"Kiranaa": "Member"},
                        {"Kiranaa": veille - 90 * 86400}, depuis=veille)[0]
        self.assertEqual(veille, c.at)

    def test_dans_la_fenetre_la_date_de_l_api_l_emporte(self):
        veille = int(time.time()) - 86400
        juste = veille + 3600
        c = roster.diff({}, {"Kiranaa": "Member"}, {"Kiranaa": juste},
                        depuis=veille)[0]
        self.assertEqual(juste, c.at)


class Redatage(unittest.TestCase):
    """Les arrivées déjà journalisées à la date du relevé se corrigent seules."""

    LILOULOVE = 8784019565

    def _journal(self, s, lignes):
        with open(s._journal(), "w", encoding="utf-8") as fh:
            for at, nom, kind in lignes:
                fh.write(json.dumps({"at": at, "member": nom, "kind": kind,
                                     "from": "", "to": "Member"}) + "\n")

    def test_une_arrivee_mal_datee_reprend_sa_vraie_date(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            constat = int(time.time()) - 3600
            self._journal(s, [(constat, "Liloulove", "arrivee")])
            s.record([("Liloulove", "Member", self.LILOULOVE)])
            ligne = s.history()[0]
            self.assertEqual(roster.date_entree(self.LILOULOVE), ligne.at)

    def test_un_parti_garde_la_sienne(self):
        """Il n'est plus dans l'effectif : l'API n'a plus de date à donner."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            constat = int(time.time()) - 3600
            self._journal(s, [(constat, "Nizy", "depart"),
                              (constat, "Parti", "arrivee")])
            s.record([("Liloulove", "Member", self.LILOULOVE)])
            self.assertEqual({constat}, {c.at for c in s.history()
                                         if c.member in ("Nizy", "Parti")})

    def test_le_redatage_ne_se_fait_qu_une_fois(self):
        """Sinon chaque relevé relirait et réécrirait tout le journal."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            self._journal(s, [(int(time.time()) - 3600, "Liloulove", "arrivee")])
            s.record([("Liloulove", "Member", self.LILOULOVE)])   # corrige
            fausse = int(time.time()) - 7200
            self._journal(s, [(fausse, "Liloulove", "arrivee")])
            s.record([("Liloulove", "Member", self.LILOULOVE)])   # n'y touche plus
            self.assertEqual(fausse, s.history()[0].at)

    def test_une_ligne_illisible_survit_au_redatage(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            with open(s._journal(), "w", encoding="utf-8") as fh:
                fh.write('{"at": 1, "member": "Liloulove", "kind": "arrivee",'
                         ' "from": "", "to": "Member"}\n')
                fh.write('{"at": 17, "member": "Tronq\n')
            s.record([("Liloulove", "Member", self.LILOULOVE)])
            self.assertIn("Tronq", open(s._journal(), encoding="utf-8").read())

    def test_une_date_posterieure_au_constat_est_refusee(self):
        """On ne peut pas avoir vu arriver quelqu'un avant qu'il n'arrive : si
        la date décodée dépasse le constat, c'est elle qui a tort."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            # Le constat s'ancre sur la date decodee, jamais sur l'horloge : le
            # cas eprouve ici veut un constat ANTERIEUR a elle, et LILOULOVE est
            # une date figee. Compte a rebours depuis time.time(), l'essai
            # cessait de porter sur quoi que ce soit des que le monde depassait
            # cette date-la -- il l'a fait le 27 aout 2026, et l'essai est
            # tombe tout seul.
            constat = roster.date_entree(self.LILOULOVE) - 86400
            self._journal(s, [(constat, "Liloulove", "arrivee")])
            s.record([("Liloulove", "Member", self.LILOULOVE)])
            self.assertEqual(constat, s.history()[0].at)

    def test_un_flux_sans_le_champ_ne_touche_a_rien(self):
        """Une vieille API, ou un flux tronqué : on ne réécrit pas le journal
        sur la foi de ce qu'on n'a pas reçu."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            self._journal(s, [(int(time.time()), "Liloulove", "arrivee")])
            avant = open(s._journal(), encoding="utf-8").read()
            s.record([("Liloulove", "Member")])
            self.assertEqual(avant, open(s._journal(), encoding="utf-8").read())


class Journal(unittest.TestCase):

    # Une guilde quelconque, et non celle du mainteneur : celle-ci a des
    # mouvements repris d'un autre exemplaire, qui compteraient dans le journal
    # et brouilleraient ce qu'on mesure ici — les relevés eux-mêmes.
    def store(self, dossier):
        return roster.RosterStore(dossier, "essai")

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


class Retention(unittest.TestCase):
    """Le journal ne garde rien au-delà de sa fenêtre de rétention."""

    def store(self, dossier):
        return roster.RosterStore(dossier, "essai")

    def _ecrire(self, s, lignes):
        import json
        with open(s._journal(), "w", encoding="utf-8") as fh:
            for at, nom in lignes:
                fh.write(json.dumps({"at": at, "member": nom, "kind": "arrivee",
                                     "from": "", "to": "Member"}) + "\n")

    def test_les_lignes_trop_vieilles_ne_sont_plus_rendues(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            maintenant = int(time.time())
            perime = maintenant - (roster.RETENTION_JOURS + 10) * 86400
            self._ecrire(s, [(perime, "Vieux"),
                             (maintenant - 2 * 86400, "Recent")])
            self.assertEqual(["Recent"], [c.member for c in s.history()])

    def test_elaguer_reecrit_le_fichier(self):
        import time
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            maintenant = int(time.time())
            perime = maintenant - (roster.RETENTION_JOURS + 10) * 86400
            self._ecrire(s, [(perime, "Vieux"),
                             (maintenant - 2 * 86400, "Recent")])
            self.assertEqual(1, s.elaguer())
            with open(s._journal(), encoding="utf-8") as fh:
                self.assertEqual(1, sum(1 for l in fh if l.strip()))
            # Deux passages de suite n'écartent rien de plus.
            self.assertEqual(0, s.elaguer())

    def test_un_relevé_elague_au_passage(self):
        with tempfile.TemporaryDirectory() as d:
            s = self.store(d)
            s.record([("Dale", "Member")])
            s.record([("Dale", "Member"), ("Nizy", "Member")])
            self.assertEqual(1, len(s.history()))


class ElagageSur(unittest.TestCase):
    """L'élagage ne doit jamais faire perdre ce qu'il n'a pas compris."""

    def test_une_ligne_illisible_survit_a_l_elagage(self):
        """Fichier tronqué par une coupure : la reconstruire à partir de ce
        qu'on a su lire l'aurait effacée."""
        import time
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            maintenant = int(time.time())
            with open(s._journal(), "w", encoding="utf-8") as fh:
                fh.write('{"at": %d, "member": "Vieux", "kind": "arrivee",'
                         ' "from": "", "to": "Member"}\n'
                         % (maintenant
                            - (roster.RETENTION_JOURS + 10) * 86400))
                fh.write('{"at": %d, "member": "Recent", "kind": "arrivee",'
                         ' "from": "", "to": "Member"}\n' % maintenant)
                fh.write('{"at": 17, "member": "Tronq\n')     # ligne coupée
            self.assertEqual(1, s.elaguer())
            with open(s._journal(), encoding="utf-8") as fh:
                restant = [l for l in fh if l.strip()]
            self.assertEqual(2, len(restant))
            self.assertIn("Tronq", "".join(restant))
            self.assertNotIn("Vieux", "".join(restant))

    def test_rien_de_vieux_rien_a_reecrire(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "essai")
            s.record([("Dale", "Member")])
            s.record([("Dale", "Member"), ("Nizy", "Member")])
            avant = open(s._journal(), encoding="utf-8").read()
            self.assertEqual(0, s.elaguer())
            self.assertEqual(avant, open(s._journal(), encoding="utf-8").read())


class Reprise(unittest.TestCase):
    """Ce qu'un autre exemplaire a constaté avant que ce journal n'existe.

    L'API ne rend qu'un état : sans reprise, ces mouvements seraient perdus
    pour toujours — non parce qu'ils ne sont pas arrivés, mais parce que
    personne ne les a dits à cet exemplaire-ci.
    """

    LUNE = "105906237"

    def test_la_reprise_verse_les_mouvements(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, self.LUNE)
            s.record([("Paty", "Officer")])
            journal = s.history()
            self.assertEqual(["Paty", "Thysela"],
                             sorted(c.member for c in journal))
            self.assertTrue(all(c.kind == "grade" for c in journal))
            thysela = next(c for c in journal if c.member == "Thysela")
            self.assertTrue(thysela.promotion)

    def test_la_reprise_ne_se_fait_qu_une_fois(self):
        """Sans témoin, chaque relevé la rejouerait : deux lignes, puis quatre."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, self.LUNE)
            for _ in range(3):
                s.record([("Paty", "Officer")])
            self.assertEqual(2, len(s.history()))

    def test_une_ligne_effacee_ne_revient_pas(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, self.LUNE)
            s.record([("Paty", "Officer")])
            s.clear()
            s.record([("Paty", "Officer")])
            self.assertEqual([], s.history())

    def test_un_journal_qui_les_a_deja_ne_double_pas(self):
        """Celui du mainteneur les contient : il ne doit pas les voir deux fois."""
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, self.LUNE)
            s._ajouter([roster.Change(1786369686, "Paty", "grade",
                                      "Member", "Officer")])
            s.record([("Paty", "Officer")])
            self.assertEqual(1, [c.member for c in s.history()].count("Paty"))

    def test_les_autres_guildes_ne_reprennent_rien(self):
        with tempfile.TemporaryDirectory() as d:
            s = roster.RosterStore(d, "689325")
            s.record([("Xiom", "HighOfficer")])
            self.assertEqual([], s.history())


if __name__ == "__main__":
    unittest.main()
