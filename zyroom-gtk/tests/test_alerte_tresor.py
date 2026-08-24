"""La cloche a le droit de parler du trésor, et de lui seul parmi les mouvements.

La règle du projet est qu'un mouvement ne sonne pas : ranger douze matières
ferait sonner douze fois, et l'alerte qui comptait se perdrait dans le tas. Le
trésor y échappe pour la raison même qui fonde la règle — un relevé rapporte au
plus **un** mouvement d'argent, jamais douze.

Ce qui est demandé ici est une alerte de mouvement, pas un seuil : un trésor de
guilde n'a pas de valeur basse qui alarme, ce qu'un officier veut savoir c'est
qu'on y a puisé.
"""

import os
import sys
import tempfile
import unittest
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import alerts, movements                              # noqa: E402
from zyroom.watch import WatchStore, KIND_MONEY                   # noqa: E402


@dataclass
class FauxInventaire:
    key: str = "chest1"
    label: str = "Coffre 1"
    items: list = field(default_factory=list)


@dataclass
class FausseEntite:
    money: str = "79000000"
    created: int = 0
    inventories: list = field(default_factory=lambda: [FauxInventaire()])


def mouvement_argent(avant: int, apres: int) -> list:
    """Ce que `movements.diff` produit quand le trésor a bougé."""
    return movements.diff({movements.MONEY_KEY: {movements.MONEY_SIG: avant}},
                          {movements.MONEY_KEY: {movements.MONEY_SIG: apres}},
                          FausseEntite(), ts=1_787_350_189.0)


class LaCloche(unittest.TestCase):

    def test_rien_tant_que_personne_n_a_demandé(self):
        """La cloche ne porte que ce qu'on lui a demandé de guetter."""
        self.assertEqual([], alerts.money_alerts(
            mouvement_argent(79_000_000, 78_000_000), surveille=False))

    def test_une_sortie_est_annoncée_avec_son_montant(self):
        alertes = alerts.money_alerts(
            mouvement_argent(79_000_000, 78_000_000), surveille=True)
        self.assertEqual(1, len(alertes))
        self.assertEqual("money", alertes[0].kind)
        self.assertIn("1 000 000", alertes[0].title)
        self.assertIn("sortis", alertes[0].title)
        self.assertIn("79 000 000", alertes[0].detail)
        self.assertIn("78 000 000", alertes[0].detail)

    def test_une_entrée_aussi(self):
        """Dans un sens ou dans l'autre : c'est le mouvement qui compte."""
        alertes = alerts.money_alerts(
            mouvement_argent(79_000_000, 79_040_000), surveille=True)
        self.assertEqual(1, len(alertes))
        self.assertIn("40 000", alertes[0].title)
        self.assertIn("entrés", alertes[0].title)

    def test_un_trésor_immobile_ne_dit_rien(self):
        self.assertEqual([], alerts.money_alerts(
            mouvement_argent(79_000_000, 79_000_000), surveille=True))

    def test_les_mouvements_d_objets_restent_muets(self):
        """Seul le trésor échappe à la règle ; les objets vont au journal."""
        objets = movements.diff({"chest1": {"ambre.sitem|250": 10}},
                                {"chest1": {"ambre.sitem|250": 400}},
                                FausseEntite())
        self.assertEqual(1, len(objets))          # le mouvement existe
        self.assertEqual([], alerts.money_alerts(objets, surveille=True))


class LaSurveillanceSePose(unittest.TestCase):

    def magasin(self) -> WatchStore:
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        return WatchStore(os.path.join(self.dossier.name, "guard.json"))

    def test_posée_puis_levée(self):
        w = self.magasin()
        self.assertFalse(w.money_watched())
        w.set_money_watched(True)
        self.assertTrue(w.money_watched())
        w.set_money_watched(False)
        self.assertFalse(w.money_watched())

    def test_elle_survit_à_la_fermeture(self):
        """Une surveillance se pose une fois, pas à chaque lancement."""
        w = self.magasin()
        w.set_money_watched(True)
        self.assertTrue(WatchStore(w._path).money_watched())

    def test_le_trésor_ne_passe_pas_pour_un_objet_disparu(self):
        """Sans garde, il serait cherché dans les inventaires, introuvable,
        signalé « disparu » — puis retiré de la liste au premier relevé."""
        w = self.magasin()
        w.set_money_watched(True)
        resultat = alerts.watch_alerts(FausseEntite(), w, lambda s: s)
        self.assertEqual([], resultat)
        self.assertTrue(w.money_watched())        # toujours là

    def test_l_entrée_porte_son_genre(self):
        w = self.magasin()
        w.set_money_watched(True)
        self.assertEqual(KIND_MONEY,
                         w.items()[movements.MONEY_SIG]["kind"])


if __name__ == "__main__":
    unittest.main()
