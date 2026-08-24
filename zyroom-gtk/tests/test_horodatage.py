"""La date d'un mouvement : celle du relevé, pas celle de la synchronisation.

Le journal datait chaque mouvement de `time.time()`, l'instant où
l'application relevait l'entité. Ouvrir l'application tous les soirs vers la
même heure donnait donc un journal où chaque jour portait la même heure, et
trois jours d'absence s'écrasaient sur l'instant du retour — 447 mouvements
datés « 16/08 17:27:02 » dans le journal de la guilde, qui était le rattrapage
d'une semaine.

L'API ne recalcule pas un flux à la demande : elle sert le dernier qu'elle ait
mis en cache, et l'inscrit dans la balise racine (`created`, à côté de
`cached_until`). L'écart se compte en heures — le flux de personnage relevé le
22 août 2026 à 01h32 portait `created` au 21 à 14h48, soit près de onze heures
plus tôt. C'est cette date-là que le journal doit porter.

Ce qu'aucun de ces tests ne prétend, c'est que ce soit l'heure du mouvement :
l'API rend un état, jamais un historique, et pas un item ne porte de date. On
sait seulement qu'un mouvement a eu lieu entre deux relevés, et la date du
relevé est la meilleure borne que le flux fournisse.
"""

import os
import sys
import time
import unittest
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import movements, ryzom_api                           # noqa: E402


#: Le relevé du 22 août 2026 à 00h09, tel que l'API l'a horodaté.
RELEVE = 1787350189

#: Ce que portait le flux de personnage servi la même nuit : dix heures plus tot.
RELEVE_ANCIEN = 1787316521


@dataclass
class FauxInventaire:
    key: str = "chest1"
    label: str = "Coffre 1"
    items: list = field(default_factory=list)


@dataclass
class FausseEntite:
    """Le strict nécessaire pour `movements.diff` : des inventaires, une date."""
    created: int = 0
    inventories: list = field(default_factory=lambda: [FauxInventaire()])


class DateDuReleve(unittest.TestCase):
    """`date_releve` : ce qu'on accepte du flux, et ce qu'on refuse."""

    def test_la_date_du_flux_est_retenue(self):
        self.assertEqual(float(RELEVE),
                         movements.date_releve(FausseEntite(created=RELEVE)))

    def test_sans_date_on_retombe_sur_l_horloge(self):
        """Un flux d'avant cet attribut, ou tronqué : mieux vaut approximatif."""
        for absente in (0, None, ""):
            quand = movements.date_releve(FausseEntite(created=absente))
            self.assertAlmostEqual(time.time(), quand, delta=5)

    def test_une_date_illisible_ne_fait_rien_tomber(self):
        quand = movements.date_releve(FausseEntite(created="pas un nombre"))
        self.assertAlmostEqual(time.time(), quand, delta=5)

    def test_une_entite_sans_le_champ_du_tout(self):
        """Le journal ne doit pas dépendre d'un attribut qui pourrait manquer."""
        @dataclass
        class Nue:
            inventories: list = field(default_factory=list)
        self.assertAlmostEqual(time.time(), movements.date_releve(Nue()), delta=5)

    def test_une_date_venue_de_l_avenir_est_ecartee(self):
        """Elle trahit une horloge locale en retard, pas un flux de demain.

        La laisser passer mettrait la ligne en tête du journal, où elle
        resterait jusqu'à ce que l'heure la rattrape."""
        quand = movements.date_releve(FausseEntite(created=int(time.time()) + 86400))
        self.assertAlmostEqual(time.time(), quand, delta=5)

    def test_une_date_d_avant_le_jeu_est_ecartee(self):
        """Ryzom a ouvert en septembre 2004 : rien de plus vieux n'est crédible."""
        quand = movements.date_releve(FausseEntite(created=42))
        self.assertAlmostEqual(time.time(), quand, delta=5)

    def test_une_marge_d_une_heure_est_tolérée(self):
        """Les horloges ne sont jamais tout à fait d'accord ; une heure suffit
        à absorber le désaccord sans laisser passer une date folle."""
        presque = int(time.time()) + 600
        self.assertEqual(float(presque),
                         movements.date_releve(FausseEntite(created=presque)))


class LeJournalPorteLaDateDuReleve(unittest.TestCase):
    """Bout en bout : de l'attribut du flux à la ligne du journal."""

    def test_les_objets_portent_la_date_du_flux(self):
        avant = {"chest1": {"fibre.sitem|250": 10}}
        apres = {"chest1": {"fibre.sitem|250": 22}}
        mouvements = movements.diff(avant, apres, FausseEntite(created=RELEVE))
        self.assertEqual(1, len(mouvements))
        self.assertEqual(float(RELEVE), mouvements[0].ts)
        self.assertEqual("2026-08-22", mouvements[0].when[:10])

    def test_le_tresor_aussi(self):
        """L'argent suit le même chemin que les objets, sa date comprise."""
        avant = {movements.MONEY_KEY: {movements.MONEY_SIG: 79_000_000}}
        apres = {movements.MONEY_KEY: {movements.MONEY_SIG: 79_040_000}}
        mouvements = movements.diff(avant, apres, FausseEntite(created=RELEVE))
        self.assertEqual(1, len(mouvements))
        self.assertEqual(float(RELEVE), mouvements[0].ts)

    def test_une_date_donnee_a_la_main_reste_prioritaire(self):
        """Les tests et les rejeux passent `ts` : le flux ne doit pas le voler."""
        mouvements = movements.diff({"chest1": {"a|1": 1}}, {"chest1": {"a|1": 2}},
                                    FausseEntite(created=RELEVE), ts=1234567890.0)
        self.assertEqual(1234567890.0, mouvements[0].ts)

    def test_la_date_survit_a_l_ecriture_et_a_la_relecture(self):
        """Le journal est en JSON Lines : la date doit s'y retrouver intacte."""
        import tempfile
        mouvements = movements.diff({"chest1": {"a|1": 1}}, {"chest1": {"a|1": 5}},
                                    FausseEntite(created=RELEVE))
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "journal.jsonl")
            movements.append(chemin, mouvements)
            relus = movements.load(chemin)
        self.assertEqual([float(RELEVE)], [m.ts for m in relus])


class LeFluxRendSaDate(unittest.TestCase):
    """Le parsing : `created` va de la balise racine jusqu'à l'entité."""

    GUILDE = ('<?xml version="1.0"?><ryzomapi version="1.0">'
              '<guild apikey="g0" created="{}" cached_until="1787355204" '
              'modules="G01:G02:G03"><gid>105906237</gid>'
              '<name>La Lune Eternelle</name></guild></ryzomapi>')

    PERSO = ('<?xml version="1.0"?><ryzomapi version="1.0">'
             '<character apikey="c0" created="{}" cached_until="1787355253" '
             'modules="C01"><id>689325</id><name>Haokan</name>'
             '</character></ryzomapi>')

    def test_une_guilde(self):
        ent = ryzom_api.parse_guild(self.GUILDE.format(RELEVE).encode())
        self.assertEqual(RELEVE, ent.created)

    def test_un_personnage(self):
        ent = ryzom_api.parse_character(self.PERSO.format(RELEVE_ANCIEN).encode())
        self.assertEqual(RELEVE_ANCIEN, ent.created)

    def test_un_flux_sans_l_attribut_se_lit_quand_meme(self):
        """L'attribut n'est pas documenté : il pourrait disparaître un jour."""
        sans = self.GUILDE.format(RELEVE).replace(f'created="{RELEVE}" ', "")
        self.assertEqual(0, ryzom_api.parse_guild(sans.encode()).created)

    def test_un_attribut_illisible_vaut_zero(self):
        ent = ryzom_api.parse_guild(self.GUILDE.format("hier").encode())
        self.assertEqual(0, ent.created)


if __name__ == "__main__":
    unittest.main()
