"""Application Qt ZyRoom."""
from __future__ import annotations

import sys

from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
from PySide6.QtWidgets import QApplication

from . import polices, theme
from .config import Settings
from .fenetre import APP_NAME, FenetrePrincipale


def charger_traductions_qt(app: QApplication) -> None:
    """Traduit ce que Qt affiche de son propre chef.

    Le menu du clic droit d'un champ de saisie — Annuler, Couper, Coller — ne
    vient pas de notre code : c'est Qt qui le construit, et il l'écrit en
    anglais tant qu'on ne lui a pas donné son catalogue. Une fenêtre française
    avec un menu anglais dedans, c'est le genre de détail qui fait douter du
    reste.

    Deux catalogues, pas un : `qtbase` porte les widgets, `qt` les modules qui
    s'y ajoutent. Absents — un paquet allégé, une distribution qui les sépare
    —, on continue sans : c'est laid, pas cassé.
    """
    langue = Settings().language or QLocale.system().name()[:2]
    if langue.startswith("en"):
        return                       # Qt parle deja anglais
    dossier = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for nom in ("qtbase", "qt"):
        traducteur = QTranslator(app)
        if traducteur.load(f"{nom}_{langue}", dossier):
            app.installTranslator(traducteur)


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
    charger_traductions_qt(app)
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
