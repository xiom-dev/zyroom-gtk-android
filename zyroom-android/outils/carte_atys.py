#!/usr/bin/env python3
"""Fabrique la carte d'Atys embarquée dans les deux portages.

À quoi elle sert : situer ses bêtes. Le flux du personnage donne la position de
chaque monture et mektoub — `<position x="10328" y="-2316"/>` — et sans fond de
carte ce sont deux nombres qui ne disent rien.

**D'où vient l'image.** De `nimetu/ryzom_map_tiles`, qui publie la carte du
monde sous licence LGPL-3.0 — le même auteur que les traductions dont nous
tirons déjà les noms d'avant-postes. Rien n'est emprunté à un service qui
pourrait fermer : l'image est téléchargée ici, réduite, et embarquée.

**Le repère.** L'image fait 10 000 × 7 500 pixels à deux unités de jeu par
pixel. Mais il n'y a **pas une origine unique** : la carte du monde est un
assemblage, et les positions que rend l'API sont locales à la région où l'on se
trouve. Voir `regions()` — c'est le cœur de ce fichier.

    python3 outils/carte_atys.py

À relancer si Ryzom redessine sa carte.
"""
import io
import json
import os
import urllib.request

try:
    from PIL import Image
except ImportError:                                     # pragma: no cover
    raise SystemExit("Pillow est nécessaire : apt install python3-pil")

Image.MAX_IMAGE_PIXELS = None

SOURCE = ("https://raw.githubusercontent.com/nimetu/ryzom_map_tiles/"
          "master/resources/maps/atys/world.png")

#: Échelle de l'image d'origine : deux unités de jeu par pixel, partout.
UNITES_PAR_PIXEL_SOURCE = 2

#: Les deux tables de Ballistic Mystix : les bornes de chaque continent en
#: coordonnées de jeu, et la boîte qu'il occupe sur la carte du monde.
#:
#: **Il n'y a pas une origine mais une par région.** La carte du monde est un
#: assemblage : les Lacs, la jungle et le désert y sont posés côte à côte, et
#: chaque continent y est placé à sa propre position. Un repère unique plaçait
#: donc correctement ce qui était dans une région, et n'importe où ailleurs le
#: reste.
#:
#: Ces deux fichiers **donnent la correspondance directement**. On l'avait
#: d'abord retrouvée région par région, en cherchant une vue du service de
#: cartes dans l'image du monde ; huit des neuf origines ainsi calées tombaient
#: à moins de sept unités de jeu — un pixel et demi — de celles-ci. La neuvième,
#: matis, était fausse de quatorze mille unités : le calage avait accroché
#: ailleurs, et **aucune position des terres matis ne s'affichait**. C'est
#: exactement ce qu'un relevé fait à la main peut rater sans rien dire.
#:
#: Même auteur et même licence que la carte elle-même : LGPL-3.0, Meelis Mägi.
SOURCE_MONDE = ("https://raw.githubusercontent.com/nimetu/ryzom_maps/"
                "master/src/Bmsite/Maps/Resources/world.json")
SOURCE_SERVEUR = ("https://raw.githubusercontent.com/nimetu/ryzom_maps/"
                  "master/src/Bmsite/Maps/Resources/server.json")

#: Ce qui figure dans `world.json` sans être une région.
PAS_UNE_REGION = ("world", "grid")


def regions() -> tuple:
    """(nom, x1, x2, y1, y2, origine x, origine y), de la plus petite à la plus
    grande.

    L'ordre compte : la plus petite région qui contient le point l'emporte. Les
    sous-terrains du Nexus tiennent dans le Nexus, qui tient lui-même dans les
    bornes matis, et c'est toujours le plus précis qu'on veut.
    """
    monde = json.loads(_telecharge(SOURCE_MONDE))
    serveur = json.loads(_telecharge(SOURCE_SERVEUR))
    trouvees = []
    for cle, ((px1, py1), _coin) in monde.items():
        if cle in PAS_UNE_REGION or cle not in serveur:
            continue
        (gx1, gy1), (gx2, gy2) = serveur[cle]
        nom = cle.split("_", 1)[1] if "_" in cle else cle
        # L'échelle est de un pour un : la carte du monde ne redimensionne rien,
        # elle déplace. L'origine est donc une simple différence.
        trouvees.append((nom, gx1, gx2, gy1, gy2, gx1 - px1, py1 + gy1))
    trouvees.sort(key=lambda r: (r[2] - r[1]) * (r[4] - r[3]))
    return tuple(trouvees)


def _telecharge(adresse: str) -> bytes:
    with urllib.request.urlopen(adresse, timeout=120) as reponse:
        return reponse.read()

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


def kotlin(largeur: int, hauteur: int, unites: float, table: tuple) -> str:
    regions = "\n".join(
        f'        Region("{n}", {x1}, {x2}, {y1}, {y2}, {ox}, {oy}),'
        for n, x1, x2, y1, y2, ox, oy in table)
    return f"""package net.ryzom.zyroom.model

// Fichier produit par outils/carte_atys.py — ne pas modifier à la main.

/**
 * Où tombe un point d'Atys sur la carte embarquée.
 *
 * Les positions du flux — `<position x="10328" y="-2316"/>` — sont **locales à
 * la région** où se trouve le personnage : la carte du monde est un assemblage,
 * et chaque région y est posée à sa place. Un repère unique plaçait donc
 * correctement ce qui était dans une région, et n'importe où ailleurs le reste.
 *
 * La plus petite région qui contient le point l'emporte : le Nexus est inclus
 * dans les bornes matis, et il est plus précis.
 */
object CarteAtys {{
    const val LARGEUR = {largeur}
    const val HAUTEUR = {hauteur}
    const val UNITES_PAR_PIXEL = {unites}f

    /** Une région, ses bornes en coordonnées de jeu, et son origine. */
    data class Region(
        val nom: String,
        val x1: Int, val x2: Int, val y1: Int, val y2: Int,
        val ox: Int, val oy: Int,
    ) {{
        fun contient(x: Int, y: Int) = x in x1..x2 && y in y1..y2
    }}

    /** De la plus petite à la plus grande : la première qui contient gagne. */
    val REGIONS = listOf(
{regions}
    )

    /** La région d'un point, ou rien si aucune ne le couvre. */
    fun regionDe(x: Int, y: Int): Region? = REGIONS.firstOrNull {{ it.contient(x, y) }}

    /** Le point du jeu, en pixels de la carte, ou rien s'il n'est sur aucune. */
    fun pixel(x: Int, y: Int): Pair<Float, Float>? {{
        val region = regionDe(x, y) ?: return null
        val px = (x - region.ox) / UNITES_PAR_PIXEL
        val py = (region.oy - y) / UNITES_PAR_PIXEL
        if (px !in 0f..LARGEUR.toFloat() || py !in 0f..HAUTEUR.toFloat()) return null
        return px to py
    }}

    /** Vrai si le point tombe sur la carte : hors d'elle, on ne montre rien. */
    fun contient(x: Int, y: Int): Boolean = pixel(x, y) != null
}}
"""


def python(largeur: int, hauteur: int, unites: float, table: tuple) -> str:
    regions = "\n".join(
        f'    ("{n}", {x1}, {x2}, {y1}, {y2}, {ox}, {oy}),'
        for n, x1, x2, y1, y2, ox, oy in table)
    return f'''"""Où tombe un point d'Atys sur la carte embarquée.

Fichier produit par ../zyroom-android/outils/carte_atys.py — ne pas modifier à
la main.

Les positions du flux sont **locales à la région** où se trouve le personnage :
la carte du monde est un assemblage, et chaque région y est posée à sa place.
La plus petite région qui contient le point l'emporte — le Nexus est inclus dans
les bornes matis, et il est plus précis.
"""
import os

LARGEUR = {largeur}
HAUTEUR = {hauteur}
UNITES_PAR_PIXEL = {unites}

#: (nom, x1, x2, y1, y2, origine x, origine y), de la plus petite à la plus grande
REGIONS = (
{regions}
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
'''


def main() -> int:
    table = regions()
    print(f"{len(table)} régions lues chez Ballistic Mystix")
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
         kotlin(LARGEUR, hauteur, unites, table)),
        (os.path.join(depot, "zyroom-gtk/zyroom/carte.py"),
         python(LARGEUR, hauteur, unites, table)),
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
