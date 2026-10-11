#!/usr/bin/env python3
"""Fabrique les aperçus (1200 × 630) des pages de xiom.be.

    ./outils/apercus-xiom.py

Discord, comme les autres messageries, lit la balise `og:image` d'une page
pour afficher une vignette sous le lien. Chaque page reçoit un `apercu.png`
à côté d'elle : le titre, une ligne d'explication et l'adresse, sur les
couleurs du site.

**Aucune donnée de la guilde dans l'image.** La vignette se voit sans mot de
passe, par quiconque voit le lien : forage, MP, ZyRoom et OP montrent donc
leur titre, jamais une capture de leur contenu.
"""
from __future__ import annotations

import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(RACINE, "site-domaine")

LARGEUR, HAUTEUR = 1200, 630
FOND = (16, 23, 26)
SURFACE = (23, 34, 38)
SARCELLE = (63, 122, 104)
OR = (232, 193, 90)
FAIBLE = (154, 168, 165)

GRAS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
NORMAL = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# dossier, titre, sous-titre, icone (None = le croissant de lune du site)
PAGES = (
    ("carte", "Carte de La Lune Éternelle",
     "Où vivent les membres de la guilde", None),
    ("forage", "Relevé de forage des Primes",
     "Où et quand sortent les matières suprêmes et excellentes", None),
    ("mp", "MP du hall de guilde",
     "Les MP à forer pour les recettes, d'après le stock du hall", None),
    ("zyroom", "ZyRoom",
     "Les inventaires de La Lune Éternelle, dans le navigateur",
     os.path.join(RACINE, "zyroom-gtk", "data", "net.ryzom.zyroomgtk.svg")),
    ("OP", "Guerre d'OP",
     "Trier ensemble les participants des guerres d'avant-poste", None),
)


def police(chemin: str, taille: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(chemin, taille)


def lune(taille: int) -> Image.Image:
    """Le croissant de la favicon : un disque sarcelle mange par le fond."""
    fois = 4  # dessine en grand puis reduit : bords lisses
    t = taille * fois
    im = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = t * 13 / 32
    d.ellipse((t / 2 - r, t / 2 - r, t / 2 + r, t / 2 + r), fill=SARCELLE)
    r2, cx, cy = t * 11 / 32, t * 20 / 32, t * 12 / 32
    d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), fill=(0, 0, 0, 0))
    return im.resize((taille, taille), Image.LANCZOS)


def svg(chemin: str, taille: int) -> Image.Image:
    # GdkPixbuf lit le SVG : deja la, puisque ZyRoom-GTK en depend
    import gi
    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf
    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(chemin, taille, taille)
    with tempfile.NamedTemporaryFile(suffix=".png") as png:
        pb.savev(png.name, "png", [], [])
        return Image.open(png.name).convert("RGBA")


def lignes(texte: str, fonte, largeur: int, d: ImageDraw.ImageDraw) -> list:
    """Coupe le texte en lignes qui tiennent dans la largeur."""
    sortie, courante = [], ""
    for mot in texte.split():
        essai = (courante + " " + mot).strip()
        if d.textlength(essai, font=fonte) <= largeur or not courante:
            courante = essai
        else:
            sortie.append(courante)
            courante = mot
    return sortie + [courante]


def carte(dossier: str, titre: str, sous: str, icone) -> None:
    im = Image.new("RGB", (LARGEUR, HAUTEUR), FOND)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, LARGEUR - 40, HAUTEUR - 40), 28,
                        fill=SURFACE, outline=(50, 66, 70), width=2)
    image = svg(icone, 260) if icone else lune(260)
    im.paste(image, (110, (HAUTEUR - 260) // 2), image)

    x, large = 430, LARGEUR - 430 - 90
    f_titre, f_sous = police(GRAS, 64), police(NORMAL, 34)
    l_titre = lignes(titre, f_titre, large, d)
    l_sous = lignes(sous, f_sous, large, d)
    haut = len(l_titre) * 78 + 24 + len(l_sous) * 46
    y = (HAUTEUR - haut) // 2 - 10
    for l in l_titre:
        d.text((x, y), l, font=f_titre, fill=OR)
        y += 78
    y += 24
    for l in l_sous:
        d.text((x, y), l, font=f_sous, fill=FAIBLE)
        y += 46
    d.text((LARGEUR - 90, HAUTEUR - 80), "xiom.be/" + dossier,
           font=police(NORMAL, 26), fill=SARCELLE, anchor="rs")
    im.save(os.path.join(SITE, dossier, "apercu.png"), optimize=True)


def accueil() -> None:
    """La racine : l'image « Xiom » elle-meme, recadree."""
    im = Image.open(os.path.join(SITE, "xiom.webp")).convert("RGB")
    echelle = max(LARGEUR / im.width, HAUTEUR / im.height)
    im = im.resize((round(im.width * echelle), round(im.height * echelle)),
                   Image.LANCZOS)
    g, h = (im.width - LARGEUR) // 2, (im.height - HAUTEUR) // 2
    im.crop((g, h, g + LARGEUR, h + HAUTEUR)).save(
        os.path.join(SITE, "apercu.jpg"), quality=88)


if __name__ == "__main__":
    accueil()
    for page in PAGES:
        carte(*page)
    print("apercus ecrits dans", SITE)
