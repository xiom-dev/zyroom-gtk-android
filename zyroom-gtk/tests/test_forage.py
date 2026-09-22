"""La table de forage : ce que rend un gisement des Primes, où et quand.

Elle est fabriquée par `outils/table_forage.py`, qui croise les deux relevés de
la guilde gardés dans `donnees/` — le classeur des saisons, complet, et la
cartographie du Tuto Forage Prime, plus récente mais inachevée. Lire un tableur
rate en silence : une colonne décalée d'un rang rend une table cohérente avec
elle-même et fausse pour la joueuse. Ces contrôles vérifient donc la **forme**
du résultat, celle que les deux sources tiennent de bout en bout.

Ce qu'ils tiennent : les quarante-sept matières des Primes sont là dans chaque
zone, sous les noms d'`armory.py` ; le suprême est complet là où l'excellente
et le choix ne sont que des taches ; les quatre zones diffèrent vraiment ; et
le Worst du classeur des saisons vaut bien pour les quatre saisons, comme la
Note 2 du tutoriel l'annonce.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, forage, meteo                          # noqa: E402

SAISONS = set(meteo.SAISONS)
CONDITIONS = {"WORST", "BAD", "GOOD", "BEST"}
TABLES = (("suprême", forage.SUPREMES), ("excellente", forage.EXCELLENTES),
          ("choix", forage.CHOIX))


def matieres_des_primes() -> set:
    """Les couples (famille, matière) qu'Armory place dans les Primes."""
    return {(famille, matiere)
            for zones in armory.SUPREMES.values()
            for familles in zones.values()
            for famille, matieres in familles.items()
            for matiere in matieres}


class Structure(unittest.TestCase):

    def test_les_quatre_zones_des_primes(self):
        for quoi, table in TABLES:
            self.assertEqual(set(meteo.ZONES), set(table), quoi)

    def test_les_noms_sont_ceux_d_armory(self):
        """Un nom qui ne se rejoint pas ne s'afficherait jamais.

        Les deux classeurs écrivent les matières autrement — en français, avec
        des surnoms (« Migno Omg AGGRO »), avec une coquille (« Scratch » pour
        « Scrath »). Le générateur les ramène tous au nom canonique ; si l'un
        lui échappait, sa matière disparaîtrait de l'écran sans un mot."""
        attendu = matieres_des_primes()
        self.assertEqual(47, len(attendu))
        for quoi, table in TABLES:
            for zone, matieres in table.items():
                self.assertLessEqual(set(matieres), attendu, f"{quoi}/{zone}")

    def test_les_créneaux_sont_bien_formés(self):
        for quoi, table in TABLES:
            for zone, matieres in table.items():
                for couple, creneaux in matieres.items():
                    self.assertTrue(creneaux, f"{quoi}/{zone}/{couple}")
                    for saison, condition in creneaux:
                        self.assertIn(saison, SAISONS, couple)
                        self.assertIn(condition, CONDITIONS, couple)


class LeSuprêmeEstComplet(unittest.TestCase):
    """Le classeur des saisons couvre les quarante-sept matières, zone par zone."""

    def test_chaque_zone_porte_les_quarante_sept(self):
        attendu = matieres_des_primes()
        for zone, matieres in forage.SUPREMES.items():
            self.assertEqual(attendu, set(matieres), zone)

    #: Les cinq matières où la cartographie dément la Note 2.
    #:
    #: Le classeur des saisons les donne en Worst — donc aux quatre saisons —,
    #: et la cartographie a coché autre chose pour une saison ou deux. C'est la
    #: cartographie qui l'emporte : elle teste chaque saison séparément, là où
    #: le classeur applique une règle générale. Elles sont nommées ici pour que
    #: le contrôle suivant reste lisible, et pour qu'on les revoie si la guilde
    #: tranche un jour.
    DÉMENTIES = {
        ("Terre de la Continuité", ("Boucles", "Scrath")),
        ("Terre de la Continuité", ("Résine", "Dung")),
        ("Cité Engloutie", ("Fibres", "Shu")),
        ("Cité Engloutie", ("Écorce", "Adriel")),
        ("Cité Engloutie", ("Écorce", "Beckers")),
    }

    def test_le_worst_vaut_pour_les_quatre_saisons(self):
        """Note 2, mode n°1 : un spot qui sort en Worst sort à toutes les saisons.

        Le classeur ne l'écrit qu'une fois, dans l'onglet « Printemps Reboot ».
        Si le générateur oubliait de le déplier, trois saisons sur quatre
        perdraient leur grande fenêtre de forage.

        Cinq matières y échappent, parce que la cartographie a relevé autre
        chose pour certaines de leurs saisons — et c'est elle qui gagne."""
        partielles = set()
        for zone, matieres in forage.SUPREMES.items():
            for couple, creneaux in matieres.items():
                saisons = {s for s, c in creneaux if c == "WORST"}
                if len(saisons) not in (0, 4):
                    partielles.add((zone, couple))
        self.assertEqual(self.DÉMENTIES, partielles)

    def test_une_vingtaine_de_matières_par_zone_sortent_en_worst(self):
        for zone in meteo.ZONES:
            _q, groupes = meteo.sortie_de(0, zone, "worst")
            n = sum(len(m) for m in groupes.values())
            self.assertTrue(20 <= n <= 30, f"{zone} : {n}")


class LesQuatreZonesDiffèrent(unittest.TestCase):
    """Ce pour quoi toute la table a été refaite.

    L'ancienne version lisait une feuille de résumé du tutoriel et la servait
    aux quatre colonnes. Confrontée aux onglets de zone, cette feuille colle
    aux Sources Interdites et diverge des trois autres : c'était donc les
    Sources Interdites affichées partout.
    """

    def test_aucune_zone_n_est_la_copie_d_une_autre(self):
        vues = {zone: frozenset(
            (couple, frozenset(creneaux))
            for couple, creneaux in forage.SUPREMES[zone].items())
            for zone in meteo.ZONES}
        for a in meteo.ZONES:
            for b in meteo.ZONES:
                if a != b:
                    self.assertNotEqual(vues[a], vues[b], f"{a} == {b}")

    def test_un_créneau_où_les_zones_ne_disent_pas_la_même_chose(self):
        """Automne par temps mauvais : seules les Sources sortent du suprême.

        C'est le cas qui a décidé de la mise en page — chaque colonne annonce
        sa propre qualité sous le nom de la zone."""
        automne = meteo.SAISONS.index("AUTOMNE")
        rendu = {z: meteo.sortie_de(automne, z, "bad")[0] for z in meteo.ZONES}
        self.assertEqual(meteo.SUPREME, rendu["Sources Interdites"])
        for zone in ("Terre de la Continuité", "Cité Engloutie",
                     "Profondeurs Interdites"):
            self.assertEqual(meteo.EXCELLENTE, rendu[zone])


class LesContinentsRestentÀPart(unittest.TestCase):
    """L'onglet des excellentes ne parle pas des Primes, et on ne l'y mêle pas."""

    def test_quarante_sept_matières_deux_saisons_deux_conditions(self):
        self.assertEqual(47, len(forage.EXCELLENTES_CONTINENTS))
        for couple, creneaux in forage.EXCELLENTES_CONTINENTS.items():
            self.assertEqual(4, len(creneaux), couple)
            self.assertEqual(2, len({s for s, _c in creneaux}), couple)

    def test_elle_ne_sert_à_aucune_colonne_des_primes(self):
        """Le contrôle qui empêche de refaire l'erreur.

        Ces excellentes-là sortent au Gouffre d'Ichor ou à la Porte des Vents.
        Les afficher sous « Sources Interdites » reviendrait à envoyer la
        joueuse forer au mauvais bout d'Atys."""
        for zone in meteo.ZONES:
            for couple, creneaux in forage.EXCELLENTES_CONTINENTS.items():
                for saison_cle, condition in creneaux:
                    saison = meteo.SAISONS.index(saison_cle)
                    qualite = meteo.qualite_de(zone, *couple, saison, condition)
                    if qualite == meteo.EXCELLENTE:
                        # La cartographie des Primes peut tomber d'accord par
                        # hasard ; ce qu'on interdit, c'est qu'elle en herite.
                        self.assertIn(
                            (saison_cle, condition),
                            forage.EXCELLENTES[zone].get(couple, set()),
                            f"{zone}/{couple} vient des continents")


if __name__ == "__main__":
    unittest.main()
