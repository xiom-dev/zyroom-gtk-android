"""Où tombe un point d'Atys sur la carte embarquée.

Fichier produit par ../zyroom-android/outils/carte_atys.py — ne pas modifier à
la main.

Les positions du flux sont en coordonnées du monde. La carte les couvre de
(6112, 7876) au coin haut-gauche jusqu'à
(26112, -7124) au coin bas-droit,
à raison de 5 unités de jeu par pixel.
"""
import os

LARGEUR = 4000
HAUTEUR = 3000
UNITES_PAR_PIXEL = 5.0
X0, Y0 = 6112, 7876

#: L'image, à côté de ce fichier : le Makefile recopie le paquet en entier.
CHEMIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "cartes", "atys.webp")


def pixel(x: int, y: int) -> tuple[float, float]:
    """Le point du jeu, en pixels de la carte.

    L'axe des ordonnées descend dans l'image et monte dans le jeu."""
    return ((x - X0) / UNITES_PAR_PIXEL, (Y0 - y) / UNITES_PAR_PIXEL)


def contient(x: int, y: int) -> bool:
    """Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien."""
    px, py = pixel(x, y)
    return 0 <= px <= LARGEUR and 0 <= py <= HAUTEUR
