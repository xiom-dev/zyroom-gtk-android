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
    ("bagne", 467, 1611, -11320, -9742, -8473, -6027),
    ("sources", 2445, 3901, -11437, -9626, 1287, -2764),
    ("nexus", 7789, 9786, -8346, -6054, -804, -424),
    ("terre", 122, 3062, -15856, -13100, -2792, -8166),
    ("route_gouffre", 5274, 7371, -16983, -9423, -933, -5459),
    ("fyros", 15753, 26084, -27145, -23672, 12337, -23208),
    ("zorai", 6633, 19068, -5767, -496, 6113, 7877),
    ("tryker", 13428, 27513, -35219, -29117, 5462, -20384),
    ("matis", 30, 18736, -7995, 211, 6111, 7876),
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
