"""Le trésor au journal : les dappers qui entrent et qui sortent.

L'API rend l'argent à part des coffres (`<money>`), et l'application ne
l'affichait qu'en bas de la fenêtre — un nombre du jour, sans mémoire. Il suit
maintenant le même chemin que les objets : l'instantané le porte sous une clé
réservée, la comparaison de deux instantanés en tire un mouvement.

Le cas qui a dicté le reste est le tout premier relevé après la mise à jour :
l'instantané précédent, écrit par l'ancienne version, ne connaît pas l'argent.
Sans garde, le journal s'ouvrirait sur une entrée de soixante-dix-neuf
millions de dappers qui n'a jamais eu lieu.
"""

import os
import sys
import unittest
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import alerts, movements                              # noqa: E402


@dataclass
class FauxInventaire:
    key: str = "chest1"
    label: str = "Coffre 1"
    items: list = field(default_factory=list)
    capacity: int = 0
    total_volume: float = 0.0
    masked: bool = False


@dataclass
class FausseEntite:
    money: str = ""
    inventories: list = field(default_factory=list)


def instantane(argent: str) -> dict:
    return alerts.build_snapshot(FausseEntite(money=argent,
                                              inventories=[FauxInventaire()]))


class Instantane(unittest.TestCase):

    def test_le_tresor_y_entre_quand_l_api_le_donne(self):
        snap = instantane("79000000")
        self.assertEqual({movements.MONEY_SIG: 79000000},
                         snap[movements.MONEY_KEY])

    def test_les_coffres_restent_a_leur_place(self):
        self.assertEqual({}, instantane("79000000")["chest1"])

    def test_rien_du_tout_quand_l_api_se_tait(self):
        # Une clé absente vaut mieux qu'un zéro : au relevé suivant, un zéro
        # ferait croire que la guilde vient de tout dépenser.
        for muet in ("", "   ", "inconnu", "12.5", "-3"):
            self.assertNotIn(movements.MONEY_KEY, instantane(muet), muet)


class MouvementDuTresor(unittest.TestCase):

    def diff(self, avant: str, apres: str) -> list:
        return movements.diff(instantane(avant), instantane(apres),
                              FausseEntite(inventories=[FauxInventaire()]),
                              ts=1787500000.0)

    def test_ce_qui_entre(self):
        mv, = self.diff("79000000", "80200000")
        self.assertEqual(movements.MONEY_KEY, mv.inv_key)
        self.assertEqual(1200000, mv.delta)
        self.assertEqual((79000000, 80200000), (mv.old, mv.new))

    def test_ce_qui_sort(self):
        mv, = self.diff("80200000", "79000000")
        self.assertEqual(-1200000, mv.delta)

    def test_un_tresor_qui_ne_bouge_pas_ne_dit_rien(self):
        self.assertEqual([], self.diff("79000000", "79000000"))

    def test_le_premier_releve_ne_journalise_pas_le_magot(self):
        """L'instantané d'avant la mise à jour ignore l'argent : on se tait."""
        ancien = instantane("79000000")
        del ancien[movements.MONEY_KEY]
        self.assertEqual([], movements.diff(
            ancien, instantane("79000000"),
            FausseEntite(inventories=[FauxInventaire()])))

    def test_un_instantane_d_un_format_antérieur_ne_casse_rien(self):
        for bancal in ({movements.MONEY_KEY: "79000000"},
                       {movements.MONEY_KEY: None},
                       {movements.MONEY_KEY: {movements.MONEY_SIG: "beaucoup"}}):
            self.assertEqual([], movements.diff(
                bancal, instantane("80000000"),
                FausseEntite(inventories=[FauxInventaire()])), bancal)

    def test_le_tresor_passe_devant_les_objets(self):
        inv = FauxInventaire()
        ent = FausseEntite(money="80000000", inventories=[inv])
        avant = {"chest1": {"m01.sitem|250": 4},
                 movements.MONEY_KEY: {movements.MONEY_SIG: 79000000}}
        apres = {"chest1": {"m01.sitem|250": 9},
                 movements.MONEY_KEY: {movements.MONEY_SIG: 80000000}}
        premier, second = movements.diff(avant, apres, ent)
        self.assertEqual(movements.MONEY_KEY, premier.inv_key)
        self.assertEqual("chest1", second.inv_key)


class Lisibilite(unittest.TestCase):

    def test_les_milliers_sont_espaces(self):
        self.assertEqual("79 000 000", movements.montant(79000000))
        self.assertEqual("0", movements.montant(0))

    def test_la_ligne_copiee_se_lit(self):
        mv, = MouvementDuTresor().diff("79000000", "80200000")
        ligne = movements.describe(mv)
        self.assertIn("1 200 000 dappers entrés", ligne)
        self.assertIn("79 000 000 > 80 200 000", ligne)

    def test_une_sortie_se_dit_sortie(self):
        mv, = MouvementDuTresor().diff("80200000", "79000000")
        self.assertIn("1 200 000 dappers sortis", movements.describe(mv))

    def test_le_journal_relu_garde_le_tresor(self):
        mv, = MouvementDuTresor().diff("79000000", "80200000")
        relu = movements.Movement.from_dict(mv.as_dict())
        self.assertEqual(movements.MONEY_KEY, relu.inv_key)
        self.assertEqual(1200000, relu.delta)


class LaCloche(unittest.TestCase):

    def test_le_tresor_ne_fait_pas_sonner(self):
        """Un mouvement d'argent n'est pas une alerte : personne ne l'a demandé."""
        ent = FausseEntite(money="79000000",
                           inventories=[FauxInventaire(capacity=1000,
                                                       total_volume=10.0)])
        self.assertEqual([], alerts.volume_alerts(ent, 80))


if __name__ == "__main__":
    unittest.main()
