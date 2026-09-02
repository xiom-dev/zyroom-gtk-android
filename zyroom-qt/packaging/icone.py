#!/usr/bin/env python3
"""Fabrique les icones binaires a partir du SVG.

PyInstaller ne lit pas le SVG : il veut un `.ico` sous Windows et un `.png`
sous Linux. Plutot que de versionner des images generees -- qui divergeraient
du SVG des la premiere retouche --, on les refabrique a chaque construction.

Qt sait deja lire le SVG et ecrire du PNG ; le format ICO, lui, n'est qu'un
conteneur de PNG, qu'on assemble a la main : c'est une trentaine d'octets
d'en-tete par taille, et cela evite une dependance de plus (Pillow) pour un
fichier qu'on fabrique une fois par livraison.
"""
from __future__ import annotations

import os
import struct
import sys

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
SVG = os.path.join(RACINE, "data", "net.ryzom.zyroomqt.svg")

#: Les tailles que Windows attend dans un .ico. 256 est celle des grandes
#: vignettes de l'explorateur, 16 celle de la barre des taches.
TAILLES_ICO = (16, 24, 32, 48, 64, 128, 256)

#: La taille du PNG Linux : celle que reclament les environnements de bureau
#: pour l'icone d'une fenetre.
TAILLE_PNG = 256


def rendre(taille: int) -> QImage:
    """Le SVG dessine dans un carre de `taille` pixels, fond transparent."""
    image = QImage(QSize(taille, taille), QImage.Format.Format_RGBA8888)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    QSvgRenderer(SVG).render(peintre)
    peintre.end()
    return image


def png(image: QImage) -> bytes:
    """L'image encodee en PNG, en memoire."""
    from PySide6.QtCore import QBuffer, QByteArray
    octets = QByteArray()
    tampon = QBuffer(octets)
    tampon.open(QBuffer.OpenModeFlag.WriteOnly)
    image.save(tampon, "PNG")
    tampon.close()
    return bytes(octets.data())


def ecrire_ico(chemin: str) -> None:
    """Assemble un .ico contenant toutes les tailles, chacune en PNG."""
    images = [png(rendre(t)) for t in TAILLES_ICO]
    # En-tete ICONDIR : reserve, type 1 (icone), nombre d'images.
    entete = struct.pack("<HHH", 0, 1, len(images))
    # Chaque entree fait 16 octets ; les donnees suivent le repertoire.
    decalage = len(entete) + 16 * len(images)
    repertoire = b""
    for taille, donnees in zip(TAILLES_ICO, images):
        # 256 s'ecrit 0 dans un octet : c'est la convention du format.
        octet = 0 if taille >= 256 else taille
        repertoire += struct.pack("<BBBBHHII", octet, octet, 0, 0, 1, 32,
                                  len(donnees), decalage)
        decalage += len(donnees)
    with open(chemin, "wb") as fh:
        fh.write(entete + repertoire + b"".join(images))


def main() -> int:
    if not os.path.isfile(SVG):
        print(f"Introuvable : {SVG}", file=sys.stderr)
        return 1
    # QGuiApplication et non QApplication : on ne montre aucune fenetre, et
    # la construction peut tourner sans serveur graphique.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QGuiApplication(sys.argv)

    sortie_png = os.path.join(ICI, "zyroom-qt.png")
    rendre(TAILLE_PNG).save(sortie_png, "PNG")
    sortie_ico = os.path.join(ICI, "zyroom-qt.ico")
    ecrire_ico(sortie_ico)
    print(f"PNG {TAILLE_PNG}px : {sortie_png}")
    print(f"ICO {len(TAILLES_ICO)} tailles : {sortie_ico}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
