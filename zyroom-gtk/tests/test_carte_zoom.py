"""Le zoom des cartes reste centré.

Le défaut que ces essais gardent : en agrandissant, le déplacement restait tel
quel pendant que l'image grandissait autour de **son** milieu, et la vue partait
sur le côté. Ludo l'a vu tout de suite ; le code, lui, ne s'en plaignait pas.

Ce qui doit tenir : le point de la carte qui est au centre du cadre y reste,
qu'on agrandisse ou qu'on rapetisse. C'est de l'arithmétique, donc ça se
vérifie sans écran.
"""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from zyroom import carte                                          # noqa: E402
from zyroom.window import MainWindow                              # noqa: E402

CADRE = (700.0, 400.0)          #: largeur et hauteur du cadre, en pixels


class FausseZone:
    """Le strict nécessaire : une taille, et un dessin qu'on ne fait pas."""

    def __init__(self, largeur=CADRE[0], hauteur=CADRE[1]):
        self._l, self._h = largeur, hauteur
        self.redessine = 0

    def get_width(self):
        return self._l

    def get_height(self):
        return self._h

    def queue_draw(self):
        self.redessine += 1


class FauxPixbuf:
    def get_width(self):
        return carte.LARGEUR

    def get_height(self):
        return carte.HAUTEUR


def fenetre():
    """Une fenêtre réduite à ce dont le zoom se sert."""
    faux = types.SimpleNamespace(_betes_pixbuf=FauxPixbuf())
    faux._borner_carte = types.MethodType(MainWindow._borner_carte, faux)
    faux._gisement_zoom = types.MethodType(MainWindow._gisement_zoom, faux)
    faux.ZOOM_MAX = MainWindow.ZOOM_MAX
    return faux


def centre(etat, zone=None):
    """Le point de la carte qui se trouve au centre du cadre.

    C'est l'inverse du placement fait au dessin : `x_écran = marge + px × échelle`
    avec `marge = (largeur − image × échelle) / 2 + glissement`.
    """
    largeur, hauteur = CADRE
    base = min(largeur / carte.LARGEUR, hauteur / carte.HAUTEUR)
    echelle = base * etat["zoom"]
    return (carte.LARGEUR / 2 - etat["glissement"][0] / echelle,
            carte.HAUTEUR / 2 - etat["glissement"][1] / echelle)


def etat_de(zoom=2.0, glissement=(40.0, -25.0)):
    return {"zoom": zoom, "glissement": list(glissement),
            "depart": list(glissement), "pince_depart": None}


class ZoomCentre(unittest.TestCase):

    def test_agrandir_garde_le_centre(self):
        faux, zone, etat = fenetre(), FausseZone(), etat_de()
        avant = centre(etat)
        faux._gisement_zoom(zone, etat, MainWindow.PAS_ZOOM)
        self.assertAlmostEqual(avant[0], centre(etat)[0], delta=0.5)
        self.assertAlmostEqual(avant[1], centre(etat)[1], delta=0.5)

    def test_rapetisser_garde_le_centre(self):
        faux, zone, etat = fenetre(), FausseZone(), etat_de()
        avant = centre(etat)
        faux._gisement_zoom(zone, etat, 1 / MainWindow.PAS_ZOOM)
        self.assertAlmostEqual(avant[0], centre(etat)[0], delta=0.5)
        self.assertAlmostEqual(avant[1], centre(etat)[1], delta=0.5)

    def test_un_aller_retour_revient_au_meme_endroit(self):
        """Trois crans en avant, trois en arrière : on doit être revenu.

        Avec 1,1 pour agrandir et 0,9 pour rapetisser, on revenait à 97 % —
        jamais tout à fait chez soi. Les deux crans sont inverses l'un de
        l'autre."""
        faux, zone, etat = fenetre(), FausseZone(), etat_de()
        pas = MainWindow.PAS_ZOOM
        depart = (etat["zoom"], tuple(etat["glissement"]))
        for _ in range(3):
            faux._gisement_zoom(zone, etat, pas)
        for _ in range(3):
            faux._gisement_zoom(zone, etat, 1 / pas)
        self.assertAlmostEqual(depart[0], etat["zoom"], delta=0.01)
        self.assertAlmostEqual(depart[1][0], etat["glissement"][0], delta=1.0)
        self.assertAlmostEqual(depart[1][1], etat["glissement"][1], delta=1.0)

    def test_le_pincement_part_de_l_agrandissement_courant(self):
        """Une échelle absolue depuis le début du geste, composée avec l'existant.

        Sans cela, le premier frémissement des doigts — échelle 1,001 — ramenait
        la carte de son cadrage d'ouverture à l'échelle 1.
        """
        faux, zone, etat = fenetre(), FausseZone(), etat_de(zoom=3.0)
        faux._gisement_zoom(zone, etat, 1.001, pincement=True)
        self.assertAlmostEqual(3.003, etat["zoom"], delta=0.01)
        faux._gisement_zoom(zone, etat, 2.0, pincement=True)
        self.assertAlmostEqual(6.0, etat["zoom"], delta=0.01)


class PresDuBord(unittest.TestCase):
    """Au bord, la borne l'emporte sur le centrage — et c'est voulu.

    Garder le centre quand la vue sortirait de l'image reviendrait à montrer du
    vide. Le point ne reste alors pas tout à fait fixe, mais la carte reste
    pleine, ce qui vaut mieux."""

    def test_au_bord_la_carte_reste_pleine(self):
        faux, zone = fenetre(), FausseZone()
        etat = etat_de(zoom=2.0, glissement=(180.0, -95.0))
        faux._gisement_zoom(zone, etat, 1 / MainWindow.PAS_ZOOM)
        largeur, hauteur = CADRE
        base = min(largeur / carte.LARGEUR, hauteur / carte.HAUTEUR)
        echelle = base * etat["zoom"]
        debord_x = (carte.LARGEUR * echelle - largeur) / 2
        self.assertLessEqual(abs(etat["glissement"][0]), debord_x + 0.5)


class Bornes(unittest.TestCase):
    """La carte ne doit pas pouvoir être poussée dans le vide."""

    def test_le_debord_se_mesure_sur_l_image_pas_sur_le_cadre(self):
        faux, zone = fenetre(), FausseZone()
        # À l'échelle 1 la carte tient entière dans le cadre : aucun débord.
        glissement = [500.0, 500.0]
        faux._borner_carte(zone, 1.0, glissement)
        self.assertEqual([0.0, 0.0], glissement)

    def test_agrandie_le_debord_existe_mais_reste_borne(self):
        faux, zone = fenetre(), FausseZone()
        glissement = [10000.0, 10000.0]
        faux._borner_carte(zone, 3.0, glissement)
        largeur, hauteur = CADRE
        base = min(largeur / carte.LARGEUR, hauteur / carte.HAUTEUR)
        echelle = base * 3.0
        attendu_x = (carte.LARGEUR * echelle - largeur) / 2
        attendu_y = (carte.HAUTEUR * echelle - hauteur) / 2
        self.assertAlmostEqual(max(0.0, attendu_x), glissement[0], delta=0.5)
        self.assertAlmostEqual(max(0.0, attendu_y), glissement[1], delta=0.5)

    def test_sans_image_rien_ne_tombe(self):
        faux = types.SimpleNamespace(_betes_pixbuf=None)
        faux._borner_carte = types.MethodType(MainWindow._borner_carte, faux)
        glissement = [7.0, 7.0]
        faux._borner_carte(FausseZone(), 2.0, glissement)
        self.assertEqual([7.0, 7.0], glissement)


if __name__ == "__main__":
    unittest.main()
