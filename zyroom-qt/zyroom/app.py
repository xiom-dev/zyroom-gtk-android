"""Application Qt ZyRoom."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import polices, theme
from .config import Settings
from .fenetre import APP_NAME, FenetrePrincipale


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
    # La palette d'abord, la feuille ensuite : l'une informe le style natif,
    # l'autre pose les accents par-dessus. Voir zyroom/theme.py.
    app.setPalette(theme.palette())
    # La taille du texte voyage dans la feuille de style : posee sur
    # l'application, elle serait effacee au premier polish. Voir theme.feuille.
    app.setStyleSheet(theme.feuille(Settings().font_size))

    fenetre = FenetrePrincipale()
    fenetre.show()
    return app.exec()
