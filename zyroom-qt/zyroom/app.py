"""Application Qt ZyRoom."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from . import polices, theme
from .config import Settings
from .fenetre import APP_NAME, FenetrePrincipale


def appliquer_taille_police(app: QApplication) -> None:
    """Grossit le texte de toute l'application du nombre de points réglé.

    **Sur la police que Qt vient de choisir**, et non sur une taille écrite en
    dur : le bureau a la sienne, et lui imposer un corps fixe ferait mentir le
    réglage de GNOME. On ajoute, on ne remplace pas.

    Une police posée sur l'application se propage à tout ce qui n'en demande
    pas d'autre — y compris les symboles des boutons, qui sont du texte. Les
    deux qui ont un corps à eux, le nom gravé en bas, se calculent depuis
    celle-ci et suivent donc aussi.
    """
    reglages = Settings()
    ecart = reglages.font_offset
    if not ecart:
        return
    police = app.font()
    taille = police.pointSizeF()
    if taille > 0:
        police.setPointSizeF(taille + ecart)
    else:
        # Une police definie en pixels et non en points : cela arrive selon le
        # bureau. Un point vaut environ un pixel et un tiers.
        police.setPixelSize(max(1, police.pixelSize() + round(ecart * 4 / 3)))
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
