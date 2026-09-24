"""La table de forage : ce que rend un gisement des Primes, où et quand.

Elle est fabriquée par `outils/table_forage.py` à partir d'une seule source :
le relevé de terrain des foreuses de la guilde, saisi sur `xiom.be/forage` et
recopié dans `donnees/forage-releve-guilde.json`. **Suprême et excellente en
viennent toutes les deux**, et rien d'autre ne les décide.

Les deux tables ont été déduites, avant : le suprême d'un classeur de 2009,
l'excellente des fourchettes d'humidité du tracker d'atys.us. Confrontées aux
quatre cent vingt-six croix du relevé, ces fourchettes tombent juste deux cent
cinq fois — une sur deux. Une fourchette dit **où** l'on trouve une matière,
pas en quelle qualité elle sort, et une seule fourchette par matière ne peut de
toute façon pas décrire quatre zones sur quatre saisons.

Ici, on tient la forme de la table, sa fidélité au relevé, et la frontière
qu'elle ne doit pas franchir : les excellentes des continents ne sont pas
celles des Primes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, forage, meteo                          # noqa: E402

SAISONS = set(meteo.SAISONS)
CONDITIONS = {"WORST", "BAD", "GOOD", "BEST"}


def matieres_des_primes() -> set:
    """Les couples (famille, matière) qu'Armory place dans les Primes."""
    return {(famille, matiere)
            for zones in armory.SUPREMES.values()
            for familles in zones.values()
            for famille, matieres in familles.items()
            for matiere in matieres}


class Structure(unittest.TestCase):

    def test_les_quatre_zones_des_primes(self):
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            self.assertEqual(set(meteo.ZONES), set(table), quoi)

    def test_les_noms_sont_ceux_d_armory(self):
        """Un nom qui ne se rejoint pas disparaîtrait de l'écran sans un mot."""
        attendu = matieres_des_primes()
        self.assertEqual(47, len(attendu))
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            for zone, matieres in table.items():
                self.assertLessEqual(set(matieres), attendu, f"{quoi}/{zone}")

    def test_les_créneaux_sont_bien_formés(self):
        for quoi, table in (("suprême", forage.SUPREMES),
                            ("excellente", forage.EXCELLENTES)):
            for zone, matieres in table.items():
                for couple, creneaux in matieres.items():
                    self.assertTrue(creneaux, f"{quoi}/{zone}/{couple}")
                    for saison, condition in creneaux:
                        self.assertIn(saison, SAISONS, couple)
                        self.assertIn(condition, CONDITIONS, couple)

    def test_le_choix_reste_vide(self):
        """Aucune source ne le suit.

        Le déduire par élimination — ce qui n'est ni suprême ni excellente —
        ferait dire à l'écran plus que ce qu'on sait : le tutoriel de la guilde
        écrit qu'une saison peut n'avoir aucun pop de choix."""
        self.assertEqual({zone: {} for zone in meteo.ZONES}, forage.CHOIX)


class LeRelevéDeTerrain(unittest.TestCase):
    """Le suprême ne se déduit plus : il a été relevé source par source.

    Quatre cent vingt-six cases cochées par les foreuses sur xiom.be/forage,
    zone par zone, saison par saison, condition par condition. C'est la seule
    mesure faite dans les Primes — tout le reste en était déduit, d'Armory, du
    tracker, ou d'un classeur de 2009.
    """

    def test_les_quatre_cent_vingt_six_créneaux(self):
        creneaux = sum(len(k) for zone in forage.SUPREMES.values()
                       for k in zone.values())
        self.assertEqual(426, creneaux)

    def test_chaque_zone_en_porte_une_quarantaine(self):
        """Sept matières environ ne sortent jamais en suprême dans une zone.

        C'est une mesure, pas un catalogue : ce qui ne sort nulle part n'y
        figure pas."""
        for zone, matieres in forage.SUPREMES.items():
            self.assertTrue(38 <= len(matieres) <= 42,
                            f"{zone} : {len(matieres)}")

    def test_la_grande_fenêtre_est_l_exécrable(self):
        """Dix-sept à vingt-et-une matières par zone y sortent aux quatre saisons.

        C'est ce que le tutoriel annonçait — Note 2, mode n°1 — et ce que le
        compte à rebours de l'écran météo attend."""
        toutes = {(s, "WORST") for s in meteo.SAISONS}
        for zone, matieres in forage.SUPREMES.items():
            partout = [c for c, k in matieres.items() if toutes <= k]
            self.assertTrue(17 <= len(partout) <= 21,
                            f"{zone} : {len(partout)}")

    def test_et_les_autres_tiennent_à_un_créneau(self):
        """Dix-huit à vingt-quatre par zone, hors de la grande fenêtre."""
        toutes = {(s, "WORST") for s in meteo.SAISONS}
        for zone, matieres in forage.SUPREMES.items():
            creneau = [c for c, k in matieres.items() if not toutes <= k]
            self.assertTrue(18 <= len(creneau) <= 24,
                            f"{zone} : {len(creneau)}")

    def test_les_quatre_zones_ne_se_ressemblent_pas(self):
        """Ce pour quoi le relevé se fait zone par zone."""
        vues = {zone: frozenset((c, frozenset(k)) for c, k in m.items())
                for zone, m in forage.SUPREMES.items()}
        for a in meteo.ZONES:
            for b in meteo.ZONES:
                if a != b:
                    self.assertNotEqual(vues[a], vues[b], f"{a} == {b}")


class L_ExcellenteVientDuMêmeRelevé(unittest.TestCase):
    """Elle ne se déduit plus des fourchettes d'humidité non plus.

    Deux cent quarante-quatre créneaux, saisis sur la même page que le
    suprême : cinquante-six vus en jeu par les foreuses — les croix vertes —
    et cent quatre-vingt-huit rapportés par une autre source et cochés en
    orange, en attente de confirmation. Les deux sont affichés : une
    excellente annoncée à tort coûte un aller-retour, une excellente tue
    coûte tout le reste.
    """

    def test_deux_cent_quarante_quatre_créneaux(self):
        creneaux = sum(len(k) for zone in forage.EXCELLENTES.values()
                       for k in zone.values())
        self.assertEqual(244, creneaux)

    def test_elle_sort_surtout_hors_de_l_exécrable(self):
        """L'inverse exact du suprême, et c'est ce qui la rend utile.

        Le suprême tient dans la grande fenêtre ; l'excellente remplit les
        trois quarts du temps où celle-ci est fermée. Un écran qui se taisait
        hors de l'exécrable laissait donc la foreuse sans rien la plupart du
        temps."""
        dehors = sum(1 for zone in forage.EXCELLENTES.values()
                     for creneaux in zone.values()
                     for _s, condition in creneaux if condition != "WORST")
        self.assertGreater(dehors, 0.9 * 244)

    def test_onze_matières_sortent_dans_les_deux_qualités(self):
        """Deux spots distincts de la même matière, au même créneau.

        `qualite_de` n'en rend qu'une — la meilleure —, mais l'écran montre
        les deux : ce sont deux endroits différents où aller."""
        communs = [(zone, couple, creneau)
                   for zone, matieres in forage.SUPREMES.items()
                   for couple, creneaux in matieres.items()
                   for creneau in creneaux
                   & forage.EXCELLENTES[zone].get(couple, set())]
        self.assertEqual(11, len(communs))


class LesContinentsRestentÀPart(unittest.TestCase):
    """L'onglet des excellentes du tutoriel ne parle pas des Primes.

    Il est lu — il s'accorde sur quarante-cinq matières avec les fourchettes du
    tracker, ce qui le rend crédible — mais ses gisements sont au Gouffre
    d'Ichor ou à la Porte des Vents. Les afficher sous « Sources Interdites »
    enverrait la joueuse forer au mauvais bout d'Atys.
    """

    def test_quarante_sept_matières_deux_saisons_deux_conditions(self):
        self.assertEqual(47, len(forage.EXCELLENTES_CONTINENTS))
        for couple, creneaux in forage.EXCELLENTES_CONTINENTS.items():
            self.assertEqual(4, len(creneaux), couple)
            self.assertEqual(2, len({s for s, _c in creneaux}), couple)

    def test_l_écran_ne_l_affiche_pas(self):
        """`sortie_de` ne lit que les trois tables des Primes."""
        for zone in meteo.ZONES:
            for saison in range(4):
                for condition in CONDITIONS:
                    _q, groupes = meteo.sortie_de(saison, zone, condition)
                    trouve = {(f, m) for f, ms in groupes.items() for m in ms}
                    dans_la_table = (set(forage.SUPREMES[zone])
                                     | set(forage.EXCELLENTES[zone]))
                    self.assertLessEqual(trouve, dans_la_table, zone)


class LesNomsFrançaisDuJeu(unittest.TestCase):
    """Le journal du jeu écrit « Mignonne » ou « Colle », le relevé « Cuty »
    ou « Glue ». Une prise dont le nom ne se reconnaît pas est jetée sans
    bruit : elle ne devient jamais une croix."""

    def test_la_carapace_mignonne_est_la_cuty(self):
        from zyroom import forage_releve
        mats = forage_releve._matieres()
        texte = "fragments de carapace mignonne excellente / primes racines"
        self.assertEqual("Cuty", next(n for b, n in mats.items() if b in texte))

    def test_la_colle_est_la_glue(self):
        from zyroom import forage_releve
        mats = forage_releve._matieres()
        texte = "résines de choix de colle / primes racines"
        self.assertEqual("Glue", next(n for b, n in mats.items() if b in texte))


if __name__ == "__main__":
    unittest.main()
