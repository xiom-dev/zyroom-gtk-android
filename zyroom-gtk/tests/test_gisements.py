"""Les cartes de gisements : la table, et ce qu'elle promet.

Le piège de cette table est qu'elle échoue en silence. Une matière mal
rapprochée n'affiche pas d'erreur : elle affiche **la carte de la voisine**, et
personne ne s'en aperçoit avant d'avoir traversé les Primes pour rien.

D'où ces contrôles : chaque libellé affiché mène quelque part, chaque fichier
promis existe, et les deux façons de nommer une même matière — le français du
classeur de la guilde et l'anglais des listes de suprêmes — mènent au même
endroit.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import armory, gisements                              # noqa: E402
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

    def test_tout_libelle_mene_a_une_carte(self):
        # Sauf une : le tracker n'a aucune vue pour la résine Fung suprême,
        # alors que le classeur de la guilde la donne dans les Sources. C'est un
        # trou du site, pas du rapprochement — on le fige ici pour que le jour
        # où il se comble, le test le dise.
        muets = [(f, m) for f, m in gisements.LIBELLES
                 if not gisements.cartes("supreme", f, m)
                 and not gisements.cartes("excellent", f, m)]
        self.assertEqual([], muets)
        self.assertEqual([], gisements.cartes("supreme", "Résine", "Fung"))
        self.assertTrue(gisements.cartes("excellent", "Résine", "Fung"))

    def test_les_fichiers_promis_existent(self):
        absents = []
        for qualite in ("supreme", "excellent"):
            for famille, matiere in gisements.LIBELLES:
                for chemin in gisements.cartes(qualite, famille, matiere):
                    if not os.path.exists(chemin):
                        absents.append(os.path.basename(chemin))
        self.assertEqual([], sorted(set(absents)))

    def test_aucune_image_orpheline(self):
        """Rien ne traîne dans le dossier qui ne soit dans la table."""
        citees = {os.path.basename(c)
                  for qualite in ("supreme", "excellent")
                  for famille, matiere in gisements.LIBELLES
                  for c in gisements.cartes(qualite, famille, matiere)}
        presentes = set(os.listdir(gisements.DOSSIER))
        self.assertEqual(set(), presentes - citees)


class DeuxNomsUneMatiere(unittest.TestCase):
    """Le classeur dit « Colle », les listes de suprêmes disent « Glue »."""

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

    def test_les_deux_noms_donnent_les_memes_cartes(self):
        for famille, francais, anglais in self.PAIRES:
            for qualite in ("supreme", "excellent"):
                self.assertEqual(
                    gisements.cartes(qualite, famille, francais),
                    gisements.cartes(qualite, famille, anglais),
                    f"{francais} et {anglais} devraient mener au même endroit")

    def test_les_annotations_des_joueurs_sont_suivies(self):
        """« Beng Agro », « Yana ? », « Migno Omg AGGRO » : le nom reste lisible."""
        for famille, annote, propre in (("Ambres", "Beng Agro", "Beng"),
                                        ("Boucles", "Yana ?", "Yana"),
                                        ("Sève", "Ardente ?", "Ardente"),
                                        ("Sève", "Visc agro KKT", "Visc"),
                                        ("Carapace", "Migno Omg AGGRO",
                                         "Mignonne")):
            self.assertEqual(gisements.cartes("supreme", famille, propre),
                             gisements.cartes("supreme", famille, annote))

    def test_enola_est_une_seve_meme_classee_en_huile(self):
        """Le classeur la range en Huile, Ballistic Mystix en Sève."""
        cartes = gisements.cartes("supreme", "Huile", "Enola")
        self.assertTrue(cartes)
        self.assertEqual(gisements.cartes("supreme", "Sève", "Enola"), cartes)
        self.assertIn("sap_enola", os.path.basename(cartes[0]))


class Inconnues(unittest.TestCase):

    def test_une_matiere_inconnue_ne_rend_rien(self):
        self.assertEqual([], gisements.cartes("supreme", "Ambres", "Zorglub"))
        self.assertEqual([], gisements.cartes("supreme", "Zorglub", "Beng"))
        self.assertEqual([], gisements.humidites("supreme", "Ambres", "Zorglub"))

    def test_les_fourchettes_d_humidite_sont_plausibles(self):
        for famille, matiere in gisements.LIBELLES:
            for qualite in ("supreme", "excellent"):
                for bas, haut in gisements.humidites(qualite, famille, matiere):
                    self.assertLessEqual(0.0, bas)
                    self.assertLess(bas, haut)
                    self.assertLessEqual(haut, 100.0)


if __name__ == "__main__":
    unittest.main()
