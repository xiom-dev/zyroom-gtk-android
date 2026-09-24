"""Les gisements : la table, et ce qu'elle promet.

Le piège de cette table est qu'elle échoue en silence. Une matière mal
rapprochée n'affiche pas d'erreur : elle affiche **le gisement de la voisine**,
et personne ne s'en aperçoit avant d'avoir traversé les Primes pour rien.

D'où ces contrôles : chaque libellé affiché mène quelque part, chaque position
tombe sur la carte embarquée, et les deux façons de nommer une même matière — le
français du relevé de la guilde et l'anglais des listes de suprêmes — mènent au
même endroit.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, carte, gisements                       # noqa: E402
from zyroom.pop import POP                                        # noqa: E402


def libelles_affiches() -> set:
    """Tous les couples (famille, matière) que l'écran météo peut écrire."""
    paires = set()
    for zones in POP.values():
        for conditions in zones.values():
            for familles in conditions.values():
                for famille, matieres in familles.items():
                    paires.update((famille, m) for m in matieres)
    for table in (armory.SUPREMES, armory.EXCELLENTES):
        for saison in table.values():
            for groupes in saison.values():
                for famille, matieres in groupes.items():
                    paires.update((famille, m) for m in matieres)
    return paires


class Table(unittest.TestCase):

    def test_tout_libelle_affiche_est_connu_de_la_table(self):
        inconnus = sorted(libelles_affiches() - set(gisements.LIBELLES))
        self.assertEqual([], inconnus,
                         "l'écran affiche des matières que la table ignore ; "
                         "relance outils/table_gisements.py")

    def test_toute_matiere_a_ses_gisements_dans_les_deux_qualites(self):
        """Le relevé de bmsite couvre les 47 matières en suprême et en excellent.

        Le tracker, lui, n'avait aucune vue pour la résine Fung suprême, que le
        relevé de la guilde donne pourtant dans les Sources. Le trou est comblé.
        """
        for qualite in ("supreme", "excellent"):
            muets = [(f, m) for f, m in gisements.LIBELLES
                     if not gisements.points(qualite, f, m)]
            self.assertEqual([], muets, f"sans gisement en {qualite}")
        self.assertTrue(gisements.points("supreme", "Résine", "Fung"))

    def test_toutes_les_positions_tombent_sur_la_carte(self):
        """Un gisement qu'on ne saurait pas placer ne servirait à rien."""
        perdus = []
        for qualite in ("supreme", "excellent"):
            for famille, matiere in gisements.LIBELLES:
                for x, y, lieu in gisements.points(qualite, famille, matiere):
                    if carte.pixel(x, y) is None:
                        perdus.append((famille, matiere, x, y))
        self.assertEqual([], sorted(set(perdus)))

    def test_chaque_position_porte_un_nom_de_lieu(self):
        """Un point sans nom ne dit pas où aller."""
        sans = []
        for qualite in ("supreme", "excellent"):
            for famille, matiere in gisements.LIBELLES:
                for _x, _y, lieu in gisements.points(qualite, famille, matiere):
                    if not lieu or lieu.startswith(("region_", "continent_")):
                        sans.append((famille, matiere, lieu))
        self.assertEqual([], sorted(set(sans)))

    def test_les_suprêmes_sont_dans_les_quatre_zones_du_classeur(self):
        """Les zones que la guilde relève, et pas d'autres.

        C'est le recoupement qui vaut : le relevé de la guilde et celui de
        Ballistic Mystix ont été établis séparément, et ils nomment les mêmes
        quatre zones.
        """
        lieux = {lieu for f, m in gisements.LIBELLES
                 for _x, _y, lieu in gisements.points("supreme", f, m)}
        self.assertEqual({"Sources Interdites", "Terre de la Continuité",
                          "Cité Engloutie", "Profondeurs Interdites"}, lieux)

    def test_les_excellentes_sont_ailleurs_dans_les_primes(self):
        lieux = {lieu for f, m in gisements.LIBELLES
                 for _x, _y, lieu in gisements.points("excellent", f, m)}
        self.assertEqual(set(), lieux & {"Sources Interdites", "Cité Engloutie"})
        self.assertIn("Gouffre d'Ichor", lieux)


class DeuxNomsUneMatiere(unittest.TestCase):
    """Le relevé dit « Colle », les listes de suprêmes disent « Glue »."""

    PAIRES = (
        ("Carapace", "Grosse", "Big"),
        ("Carapace", "Mignonne", "Cuty"),
        ("Carapace", "Inteligente", "Smart"),
        ("Carapace", "Cornée", "Horny"),
        ("Résine", "Colle", "Glue"),
        ("Résine", "Lune", "Moon"),
        ("Sève", "Ardente", "Redhot"),
        ("Fibres", "Anète", "Anete"),
        ("Boucles", "Scratch", "Scrath"),
    )

    def test_les_deux_noms_donnent_les_memes_gisements(self):
        for famille, francais, anglais in self.PAIRES:
            for qualite in ("supreme", "excellent"):
                self.assertEqual(
                    gisements.points(qualite, famille, francais),
                    gisements.points(qualite, famille, anglais),
                    f"{francais} et {anglais} devraient mener au même endroit")

    def test_aucune_annotation_de_joueur_ne_s_affiche(self):
        """Le classeur porte les notes de ceux qui l'ont rempli, pas l'écran.

        « Migno Omg AGGRO » était affiché tel quel : l'abréviation d'un nom et
        l'avertissement d'un joueur, pris pour le nom d'une matière. Le
        nettoyage se fait maintenant à la fabrication de la table, si bien
        qu'aucune annotation ne peut plus atteindre l'écran — ni celles-là, ni
        celles que la guilde écrira demain."""
        for zones in POP.values():
            for conditions in zones.values():
                for familles in conditions.values():
                    for famille, matieres in familles.items():
                        for matiere in matieres:
                            self.assertNotIn(
                                "?", matiere,
                                f"{famille} / « {matiere} » porte un doute")
                            self.assertEqual(
                                1, len(matiere.split()),
                                f"{famille} / « {matiere} » porte une note")

    def test_enola_est_une_seve(self):
        """Et elle l'est partout, depuis que le relevé a remplacé le classeur.

        Le classeur de la guilde la rangeait en Huile quand le jeu la range en
        Sève, et la table portait les deux libellés pour que les deux écrans
        se rejoignent. Le relevé de xiom.be/forage l'a remplacé : plus aucune
        table ne dit « Huile / Enola », et trois libellés du classeur ont
        disparu avec lui — celui-ci, « Ardente ? » et « Visc agro KKT ».
        """
        from zyroom import armory, forage
        for quoi in (forage.SUPREMES, forage.EXCELLENTES):
            for zone in quoi.values():
                self.assertNotIn(("Huile", "Enola"), zone)
        rangees = {f for zones in armory.SUPREMES.values()
                   for familles in zones.values()
                   for f, ms in familles.items() if "Enola" in ms}
        self.assertEqual({"Sève"}, rangees)
        self.assertTrue(gisements.points("supreme", "Sève", "Enola"))


class Inconnues(unittest.TestCase):

    def test_une_matiere_inconnue_ne_rend_rien(self):
        self.assertEqual([], gisements.points("supreme", "Ambres", "Zorglub"))
        self.assertEqual([], gisements.points("supreme", "Zorglub", "Beng"))
        self.assertEqual([], gisements.humidites("supreme", "Ambres", "Zorglub"))

    def test_les_fourchettes_d_humidite_sont_plausibles(self):
        for famille, matiere in gisements.LIBELLES:
            for qualite in ("supreme", "excellent"):
                for bas, haut in gisements.humidites(qualite, famille, matiere):
                    self.assertLessEqual(0.0, bas)
                    self.assertLess(bas, haut)
                    self.assertLessEqual(haut, 100.0)


class ProchaineSortie(unittest.TestCase):
    """Le « prochaine fois dans… » que la carte d'une matière annonce.

    Chaque matière a son seuil : Zun suprême sort dès cinquante pour cent
    d'humidité, là où la grande fenêtre du suprême en demande quatre-vingt-
    trois. La carte doit donc compter pour **sa** matière, et non répéter le
    compte à rebours du titre.
    """

    @staticmethod
    def _page(conditions, cycle=100):
        """Une fausse fenêtre, avec juste ce que la méthode lit."""
        import types
        from zyroom import meteo as m
        cycles = [m.Meteo(cycle=cycle + i, condition=c, value=0.5,
                          text="uiRainy") for i, c in enumerate(conditions)]
        releve = m.MeteoAtys(cycle_courant=cycle, heure_atys=cycle * 3.0,
                             saison=m.SAISONS.index("ETE"),
                             continents={"sources": cycles, "terre": cycles})
        return types.SimpleNamespace(_meteo_affiche=releve, _meteo_releve=None)

    def setUp(self):
        from zyroom.page_gisements import PageGisements
        self.methode = PageGisements._prochaine_sortie
        self.lieux = [lieu for _x, _y, lieu
                      in gisements.points("supreme", "Ambres", "Zun")]

    def test_elle_compte_jusqu_au_premier_créneau_de_la_matière(self):
        """Le compte s'arrête au premier cycle où la matière sort quelque part.

        On ne fige pas le nombre de minutes : il suit le relevé de la guilde,
        qui bouge à mesure que les foreuses remplissent le tableau. Ce qu'on
        tient, c'est qu'il désigne bien le **premier** cycle utile."""
        from zyroom import meteo as m
        conditions = ["good", "good", "bad", "worst", "worst"]
        page = self._page(conditions)
        minutes = self.methode(page, "supreme", "Ambres", "Zun", self.lieux)
        attendu = None
        for rang, condition in enumerate(conditions):
            if rang == 0:
                continue                    # le cycle en cours ne compte pas
            if any(m.qualite_de(lieu, "Ambres", "Zun", m.SAISONS.index("ETE"),
                                condition) == m.SUPREME
                   for lieu in self.lieux if lieu in m.ZONES):
                attendu = rang * m.MINUTES_PAR_CYCLE
                break
        self.assertEqual(attendu, minutes)
        self.assertIsNotNone(attendu, "aucun créneau dans la prévision d'essai")

    def test_rien_dans_la_prévision_ne_s_invente_pas(self):
        page = self._page(["good"] * 40)
        self.assertIsNone(self.methode(page, "supreme", "Ambres", "Zun",
                                       self.lieux))

    def test_sans_relevé_météo(self):
        import types
        page = types.SimpleNamespace(_meteo_affiche=None, _meteo_releve=None)
        self.assertIsNone(self.methode(page, "supreme", "Ambres", "Zun",
                                       self.lieux))


class TextesDeLaCarte(unittest.TestCase):
    """Les deux phrases sous l'en-tête, qui suivent le cycle.

    Elles sont calculées au même endroit à l'ouverture et à chaque battement :
    une carte laissée ouverte doit dire la vérité neuf minutes plus tard, quand
    le cycle a basculé.
    """

    def _textes(self, conditions):
        from zyroom.page_gisements import PageGisements
        page = ProchaineSortie._page(conditions)
        page._gisements_actifs = lambda *a: PageGisements._gisements_actifs(
            page, *a)
        page._prochaine_sortie = lambda *a: PageGisements._prochaine_sortie(
            page, *a)
        lieux = [lieu for _x, _y, lieu
                 in gisements.points("supreme", "Ambres", "Zun")]
        return PageGisements._textes_carte(page, "supreme", "Ambres", "Zun",
                                           lieux)

    def test_rien_ne_sort_alors_on_dit_quand(self):
        """Zun ne sort pas par temps bon : la seconde ligne s'allume."""
        actifs, maintenant, apres = self._textes(["good", "good", "worst"])
        self.assertEqual(set(), actifs)
        self.assertIn("aucun des 4 gisements", maintenant)
        self.assertIn("Prochaine fois dans", apres)

    def test_quelque_chose_sort_alors_on_se_tait(self):
        """La seconde ligne n'apprendrait rien : elle reste vide."""
        actifs, maintenant, apres = self._textes(["worst", "good"])
        self.assertTrue(actifs)
        self.assertIn("gisements sur 4", maintenant)
        self.assertEqual("", apres)


if __name__ == "__main__":
    unittest.main()
