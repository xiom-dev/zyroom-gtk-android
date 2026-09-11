"""L'axe du temps sous la courbe météo : un tiret toutes les cinq minutes.

Ce que ces essais gardent. L'axe ne portait qu'un repère par quart d'heure —
cinq heures d'Atys entre deux traits. Pour viser un creux de prévision, il
fallait interpoler à l'œil sur soixante pixels, et les joueurs ont demandé
mieux. Les tirets tombent désormais toutes les cinq minutes réelles ; les
heures, elles, restent écrites au quart d'heure, faute de quoi quinze nombres
se chevaucheraient sur une largeur qui en tient cinq.

Le tracé se vérifie sans écran : on donne à la fonction de dessin un contexte
qui ne peint rien et retient ce qu'on lui demande.
"""

import os
import re
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import meteo                                         # noqa: E402
from zyroom.window import MainWindow                             # noqa: E402


def constantes_de_fenetre() -> dict:
    """Les constantes que `MainWindow` definit, telles quelles.

    Le trace en lit une dizaine, et la liste s'allonge des qu'on regle quelque
    chose : les recopier a la main condamnait les essais a tomber sur un
    AttributeError au premier ajout. `vars` ne rend que ce que la classe
    definit elle-meme, sans l'heritage de GTK.
    """
    return {nom: valeur for nom, valeur in vars(MainWindow).items()
            if nom.isupper()}


class FauxCr:
    """Un contexte Cairo qui retient les tirets de l'axe et les heures.

    Un tiret est un trait vertical de quelques points vers le bas : même
    abscisse, ordonnée qui croît de deux ou trois. La courbe, elle, va de
    travers et sur de bien plus grandes hauteurs.
    """

    #: La hauteur du dessin, telle que `dessiner` la demande plus bas.
    HAUTEUR = 300.0
    #: L'ordonnee ou se posent les heures. Lue dans la classe, et non ecrite
    #: ici : elle a bouge le jour ou le tiret allonge est venu mordre sur les
    #: chiffres, et l'essai cessait alors de voir la moindre heure -- sans
    #: rien dire d'utile.
    PIED = HAUTEUR - MainWindow.PIED_DES_HEURES

    def __init__(self):
        self.dernier = None
        self.tirets = []          #: longueur de chaque tiret, dans l'ordre
        self.textes = []

    def move_to(self, x, y):
        self.dernier = (x, y)

    def line_to(self, x, y):
        if self.dernier is not None:
            largeur = abs(x - self.dernier[0])
            hauteur = y - self.dernier[1]
            if largeur < 0.001 and 0 < hauteur <= MainWindow.LONGUEUR_TIRET_ECRIT:
                self.tirets.append(round(hauteur))
        self.dernier = (x, y)

    def show_text(self, texte):
        # La courbe ecrit aussi ses graduations d'humidite -- « 30 », « 83 »
        # -- dans la marge de gauche. Seules comptent ici les heures, posees
        # sous l'axe : on les reconnait a leur ordonnee.
        if self.dernier is not None and abs(self.dernier[1] - self.PIED) < 0.5:
            self.textes.append(texte)

    def __getattr__(self, nom):
        return lambda *a, **k: None


def dessiner():
    """Trace la courbe sur un contexte de papier, et rend ce qu'il a retenu."""
    cycles = [meteo.Meteo(cycle=1000 + i, condition="good", value=v,
                          text="uiFair")
              for i, v in enumerate((0.2, 0.5, 0.8, 0.4, 0.6))]
    releve = types.SimpleNamespace(
        heure_atys=1000 * meteo.HEURES_PAR_CYCLE + 1.0,
        cycles_des_primes=lambda: cycles)
    faux = types.SimpleNamespace(
        _meteo_affiche=releve, _meteo_releve=None,
        _settings=types.SimpleNamespace(zoom=1.0),
        **constantes_de_fenetre())
    cr = FauxCr()
    MainWindow._dessiner_courbe(faux, None, cr, 800.0, FauxCr.HAUTEUR)
    return cr


class AxeDuTemps(unittest.TestCase):

    def setUp(self):
        self.cr = dessiner()

    def test_les_heures_ecrites_tombent_au_quart_d_heure(self):
        # « 14h », « 14h15 » : jamais « 14h05 ». C'est la seule chose qui
        # rendrait l'axe illisible si les tirets emportaient le texte avec eux.
        for texte in self.cr.textes:
            with self.subTest(texte=texte):
                trouve = re.fullmatch(r"(\d{2})h(\d{2})?", texte)
                self.assertIsNotNone(trouve, f"heure mal formée : {texte}")
                minute = int(trouve.group(2) or 0)
                self.assertIn(minute, (0, 15, 30, 45))

    def test_il_y_a_plus_de_tirets_que_d_heures_ecrites(self):
        # Le defaut d'origine : autant de tirets que d'heures, un par quart
        # d'heure. Il en faut trois fois plus.
        self.assertGreater(len(self.cr.tirets), len(self.cr.textes))

    def test_deux_tirets_muets_entre_deux_heures(self):
        # Quinze minutes divisees par cinq : trois tirets, dont un porte
        # l'heure. Les bords de la fenetre peuvent en trancher un, d'ou la
        # comparaison sur le rapport plutot que sur un compte exact.
        longs = [t for t in self.cr.tirets
                 if t == MainWindow.LONGUEUR_TIRET_ECRIT]
        courts = [t for t in self.cr.tirets
                  if t == MainWindow.LONGUEUR_TIRET_MUET]
        self.assertEqual(len(longs), len(self.cr.textes))
        self.assertAlmostEqual(2.0, len(courts) / len(longs), delta=0.5)

    def test_le_tiret_muet_est_plus_court_que_celui_qui_porte_l_heure(self):
        # Sans cette difference, l'axe deviendrait un peigne ou l'on ne
        # distinguerait plus le quart d'heure du reste.
        self.assertIn(MainWindow.LONGUEUR_TIRET_MUET, self.cr.tirets)
        self.assertIn(MainWindow.LONGUEUR_TIRET_ECRIT, self.cr.tirets)
        self.assertLess(MainWindow.LONGUEUR_TIRET_MUET,
                        MainWindow.LONGUEUR_TIRET_ECRIT)
        self.assertLess(MainWindow.OPACITE_TIRET_MUET,
                        MainWindow.OPACITE_TIRET_ECRIT)


if __name__ == "__main__":
    unittest.main()
