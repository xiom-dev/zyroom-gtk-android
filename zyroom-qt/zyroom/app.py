"""Application Qt ZyRoom."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import polices, theme
from .config import Settings
from .fenetre import APP_NAME, FenetrePrincipale


def appliquer_taille_police(app: QApplication) -> None:
    """Donne à toute l'application le corps de texte réglé, en points.

    Zéro laisse la police du bureau telle quelle : c'est le comportement de
    quelqu'un qui n'a rien demandé, et son réglage GNOME reste maître.

    Une police posée sur l'application se propage à tout ce qui n'en demande
    pas d'autre — y compris les symboles des boutons, qui sont du texte, et le
    nom gravé en bas, dont le corps se calcule depuis celle-ci.
    """
    taille = Settings().font_size
    if taille <= 0:
        return
    police = app.font()
    police.setPointSizeF(float(taille))
    app.setFont(police)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv if argv is None else argv)

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    # Sous Wayland, c'est ce nom qui rattache la fenetre a son fichier
    # .desktop : sans lui, le bureau affiche une icone generique et un titre
    # "python3" dans l'alternateur de taches.
    app.setDesktopFileName("net.ryzom.zyroomqt")

    # Le style Fusion plutot que celui du bureau : c'est le seul que Qt rende
    # identiquement sous Linux et sous Windows, et le seul qui laisse la
    # feuille de style peindre sans qu'un theme natif reprenne la main --
    # exactement le probleme qu'Adwaita posait cote GTK.
    app.setStyle("Fusion")
    polices.charger()
    appliquer_taille_police(app)
    # La palette d'abord, la feuille ensuite : l'une informe le style natif,
    # l'autre pose les accents par-dessus. Voir zyroom/theme.py.
    app.setPalette(theme.palette())
    app.setStyleSheet(theme.feuille())

    fenetre = FenetrePrincipale()
    fenetre.show()
    return app.exec()
