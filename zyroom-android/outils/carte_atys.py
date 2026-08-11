#!/usr/bin/env python3
"""Fabrique la carte d'Atys embarquée dans les deux portages.

À quoi elle sert : situer ses bêtes. Le flux du personnage donne la position de
chaque monture et mektoub — `<position x="10328" y="-2316"/>` — et sans fond de
carte ce sont deux nombres qui ne disent rien.

**D'où vient l'image.** De `nimetu/ryzom_map_tiles`, qui publie la carte du
monde sous licence LGPL-3.0 — le même auteur que les traductions dont nous
tirons déjà les noms d'avant-postes. Rien n'est emprunté à un service qui
pourrait fermer : l'image est téléchargée ici, réduite, et embarquée.

**Le repère.** L'image fait 10 000 × 7 500 pixels à **deux unités de jeu par
pixel**, et son coin haut-gauche vaut (6112, 7876) en coordonnées de jeu. Cette
correspondance n'est écrite nulle part : la bibliothèque qui la porte est
absente du dépôt. Elle a été retrouvée par recoupement, en cherchant dans
l'image une vue dont on connaissait le centre et l'échelle — deux points
indépendants la confirment à 0,966 et 0,985 de corrélation.

Attention au repère : les coordonnées des primitives de `ryzomcore_leveldesign`
sont **celles du serveur**, une origine par zone, et ne se comparent pas à
celles-ci. L'API du jeu, elle, parle bien en coordonnées du monde.

    python3 outils/carte_atys.py

À relancer si Ryzom redessine sa carte.
"""
import io
import os
import urllib.request

try:
    from PIL import Image
except ImportError:                                     # pragma: no cover
    raise SystemExit("Pillow est nécessaire : apt install python3-pil")

Image.MAX_IMAGE_PIXELS = None

SOURCE = ("https://raw.githubusercontent.com/nimetu/ryzom_map_tiles/"
          "master/resources/maps/atys/world.png")

#: Échelle et origine de l'image d'origine, en coordonnées de jeu.
UNITES_PAR_PIXEL_SOURCE = 2
X0, Y0 = 6112, 7876

#: Largeur de la carte embarquée.
#:
#: Quatre mille pixels pour vingt mille unités de jeu, soit cinq unités par
#: pixel : une bête est placée à cinq mètres près, et l'image pèse un peu plus
#: d'un mégaoctet — moins que le pack de noms que l'application transporte déjà.
LARGEUR = 4000


def charge() -> Image.Image:
    print("téléchargement de la carte du monde (59 Mo)…")
    with urllib.request.urlopen(SOURCE, timeout=600) as reponse:
        return Image.open(io.BytesIO(reponse.read())).convert("RGB")


def kotlin(largeur: int, hauteur: int, unites: float) -> str:
    return f'''package net.ryzom.zyroom.model

// Fichier produit par outils/carte_atys.py — ne pas modifier à la main.

/**
 * Où tombe un point d'Atys sur la carte embarquée.
 *
 * Les positions du flux — `<position x="10328" y="-2316"/>` — sont en
 * coordonnées du monde. La carte les couvre de ({X0}, {Y0}) au coin haut-gauche
 * jusqu'à ({X0 + int(largeur * unites)}, {Y0 - int(hauteur * unites)}) au coin
 * bas-droit, à raison de {unites:g} unités de jeu par pixel.
 */
object CarteAtys {{
    const val LARGEUR = {largeur}
    const val HAUTEUR = {hauteur}
    const val UNITES_PAR_PIXEL = {unites}f
    const val X0 = {X0}
    const val Y0 = {Y0}

    /** L'abscisse d'un point du jeu, en pixels de la carte. */
    fun x(x: Int): Float = (x - X0) / UNITES_PAR_PIXEL

    /** L'ordonnée d'un point du jeu. L'axe descend dans l'image, monte dans le jeu. */
    fun y(y: Int): Float = (Y0 - y) / UNITES_PAR_PIXEL

    /** Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien. */
    fun contient(x: Int, y: Int): Boolean =
        x(x) in 0f..LARGEUR.toFloat() && y(y) in 0f..HAUTEUR.toFloat()
}}
'''


def python(largeur: int, hauteur: int, unites: float) -> str:
    return f'''"""Où tombe un point d'Atys sur la carte embarquée.

Fichier produit par ../zyroom-android/outils/carte_atys.py — ne pas modifier à
la main.

Les positions du flux sont en coordonnées du monde. La carte les couvre de
({X0}, {Y0}) au coin haut-gauche jusqu'à
({X0 + int(largeur * unites)}, {Y0 - int(hauteur * unites)}) au coin bas-droit,
à raison de {unites:g} unités de jeu par pixel.
"""
import os

LARGEUR = {largeur}
HAUTEUR = {hauteur}
UNITES_PAR_PIXEL = {unites}
X0, Y0 = {X0}, {Y0}

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
'''


def main() -> int:
    monde = charge()
    unites = UNITES_PAR_PIXEL_SOURCE * monde.width / LARGEUR
    hauteur = round(monde.height * LARGEUR / monde.width)
    carte = monde.resize((LARGEUR, hauteur), Image.LANCZOS)
    print(f"carte {LARGEUR} × {hauteur} px, {unites:g} unités de jeu par pixel")

    android = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    depot = os.path.dirname(android)
    sorties = (
        (os.path.join(android, "app/src/packRes/drawable-nodpi/carte_atys.webp"),
         None),
        (os.path.join(depot, "zyroom-gtk/zyroom/cartes/atys.webp"), None),
        (os.path.join(android,
                      "app/src/packKotlin/net/ryzom/zyroom/model/CarteAtys.kt"),
         kotlin(LARGEUR, hauteur, unites)),
        (os.path.join(depot, "zyroom-gtk/zyroom/carte.py"),
         python(LARGEUR, hauteur, unites)),
    )
    for cible, contenu in sorties:
        racine = os.path.dirname(os.path.dirname(cible))
        if not os.path.isdir(racine):
            print("passé :", cible, "(dossier absent)")
            continue
        os.makedirs(os.path.dirname(cible), exist_ok=True)
        if contenu is None:
            carte.save(cible, "WEBP", quality=80, method=6)
        else:
            with open(cible, "w", encoding="utf-8") as fh:
                fh.write(contenu)
        print(f"→ {cible}  ({os.path.getsize(cible) // 1024} ko)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
