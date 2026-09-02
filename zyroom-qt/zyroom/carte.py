"""Où tombe un point d'Atys sur la carte embarquée.

Fichier produit par ../zyroom-android/outils/carte_atys.py — ne pas modifier à
la main.

Les positions du flux sont **locales à la région** où se trouve le personnage :
la carte du monde est un assemblage, et chaque région y est posée à sa place.
La plus petite région qui contient le point l'emporte — le Nexus est inclus dans
les bornes matis, et il est plus précis.
"""
import os

LARGEUR = 4000
HAUTEUR = 3000
UNITES_PAR_PIXEL = 5.0

#: (nom, x1, x2, y1, y2, origine x, origine y), de la plus petite à la plus grande
REGIONS = (
    ("matis_island_1", 14080, 15360, -1600, -320, -552, 1740),
    ("kitiniere", 1760, 3040, -17440, -16160, -13512, -10228),
    ("bagne", 480, 1600, -11360, -9760, -8480, -6020),
    ("sources", 2560, 3840, -11360, -9760, 1284, -2760),
    ("undernexus", 7680, 11040, -9600, -8480, -808, -424),
    ("newbieland", 8160, 11360, -12320, -10240, -7660, -10040),
    ("terre", 160, 3040, -15840, -13120, -2796, -8160),
    ("nexus", 7680, 11040, -9440, -5920, -808, -424),
    ("route_gouffre", 5440, 7360, -16960, -9600, -936, -5456),
    ("fyros", 15840, 20320, -27040, -23840, 12336, -23204),
    ("zorai", 6880, 12480, -5920, -960, 6108, 7880),
    ("tryker", 13760, 20000, -34880, -29440, 5460, -20380),
    ("matis", 320, 6240, -7840, -320, -8480, 396),
)

#: L'image, à côté de ce fichier : le Makefile recopie le paquet en entier.
CHEMIN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "cartes", "atys.webp")


def region_de(x: int, y: int):
    """La région d'un point, ou None si aucune ne le couvre."""
    for region in REGIONS:
        _nom, x1, x2, y1, y2, _ox, _oy = region
        if x1 <= x <= x2 and y1 <= y <= y2:
            return region
    return None


def pixel(x: int, y: int):
    """Le point du jeu, en pixels de la carte, ou None s'il n'est sur aucune.

    L'axe des ordonnées descend dans l'image et monte dans le jeu."""
    region = region_de(x, y)
    if region is None:
        return None
    px = (x - region[5]) / UNITES_PAR_PIXEL
    py = (region[6] - y) / UNITES_PAR_PIXEL
    if not (0 <= px <= LARGEUR and 0 <= py <= HAUTEUR):
        return None
    return (px, py)


def contient(x: int, y: int) -> bool:
    """Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien."""
    return pixel(x, y) is not None
