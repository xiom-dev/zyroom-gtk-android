"""L'origine de l'application, et les avis que la licence demande.

L'AGPL ne se contente pas d'un remerciement : quand un programme qu'elle couvre
a une interface, celle-ci doit porter le copyright, l'absence de garantie, le
droit de redistribuer et le moyen de lire la licence. Le dépôt et le README le
disent déjà — mais un joueur n'ira jamais les lire, et c'est à lui que
l'obligation s'adresse.

La filiation est écrite ici : cette application traduit le zyRoom Delphi de
Misugi. C'est une œuvre dérivée, et l'AGPL interdit d'en effacer la paternité
d'origine.

**Ce que Qt n'a pas.** GTK offre un `Gtk.AboutDialog` tout fait, qui sait
afficher le texte complet d'une licence connue. Qt n'a pas d'équivalent : la
fenêtre est montée à la main, et le renvoi vers la licence se fait par un lien
vers le dépôt — où le `LICENSE.md` est au complet, comme dans le paquet livré.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QLabel, QPushButton, QScrollArea,
                               QVBoxLayout, QWidget)

from .i18n import _

DEPOT_SOURCES = "https://github.com/xiom-dev/zyroom-gtk-android"
DEPOT_ORIGINE = "https://github.com/misugi/zyroom"
COURRIEL = "ludopika@ikmail.com"

#: Ce qui n'est pas de nous et qu'on embarque. Deux de ces releves sont sous
#: LGPL, qui **oblige** a nommer leur auteur.
CREDITS = (
    ("Lettrage", "Pirata One, © Rodrigo Fuenzalida et Nicolas Massi, "
                 "SIL Open Font License 1.1"),
    ("Matières suprêmes et excellentes", "Ryzom Armory"),
    ("Noms des avant-postes", "RyzomExtra, © Meelis Mägi, GNU LGPL v3"),
    ("Carte d'Atys", "Ryzom Map Tiles, © Meelis Mägi, GNU LGPL v3"),
    ("Positions des gisements", "relevé de ballisticmystix.net, avec "
                                "l'accord de son auteur"),
    ("Symboles des familles et fonds de carte", "images du jeu, © Winch Gate"),
)


def _bloc(titre: str, corps: str) -> QWidget:
    boite = QWidget()
    colonne = QVBoxLayout(boite)
    colonne.setContentsMargins(0, 8, 0, 0)
    colonne.setSpacing(2)
    entete = QLabel(f"<b>{titre}</b>")
    colonne.addWidget(entete)
    texte = QLabel(corps)
    texte.setWordWrap(True)
    texte.setOpenExternalLinks(True)
    texte.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextBrowserInteraction)
    colonne.addWidget(texte)
    return boite


def montrer(parent, nom_appli: str, version: str) -> None:
    fen = QDialog(parent)
    fen.setWindowTitle(_("À propos de {}").format(nom_appli))
    fen.resize(520, 560)
    colonne = QVBoxLayout(fen)
    colonne.setContentsMargins(0, 0, 0, 0)

    contenu = QWidget()
    dedans = QVBoxLayout(contenu)
    dedans.setContentsMargins(16, 16, 16, 16)
    dedans.setSpacing(4)

    titre = QLabel(f"<h2>{nom_appli}</h2>")
    dedans.addWidget(titre)
    # Le numero n'est pas dans le nom de la fenetre : c'est ici qu'on vient le
    # lire quand on demande a un joueur "tu as laquelle ?".
    numero = QLabel(_("Version {}").format(version))
    numero.setObjectName("discret")
    dedans.addWidget(numero)

    dedans.addWidget(_bloc(_("Ce que c'est"), _(
        "Vos inventaires Ryzom et les coffres de la guilde, hors du jeu.<br>"
        "Dérivée du zyRoom de Misugi, écrit en Delphi pour Windows : "
        "{} en reprend les algorithmes et la lecture de l'API, "
        "et hérite donc de sa licence.").format(nom_appli)))

    dedans.addWidget(_bloc(_("Droits"),
                           "© Misugi " + _("pour le zyRoom d'origine") + "<br>"
                           "© 2026 Xiom " + _("pour ce portage")))

    dedans.addWidget(_bloc(_("Licence"), _(
        "GNU Affero General Public License, version 3 ou ultérieure.<br>"
        "Ce programme est fourni <b>sans aucune garantie</b>. Vous êtes libre "
        "de le redistribuer et de le modifier selon les termes de cette "
        "licence ; son texte complet accompagne l'application et se trouve "
        "aussi dans le dépôt.")))

    dedans.addWidget(_bloc(_("Code source"), _(
        "L'AGPL veut que l'interface dise où prendre les sources :<br>"
        '<a href="{0}">{0}</a>').format(DEPOT_SOURCES)))

    dedans.addWidget(_bloc(_("Projet d'origine"),
                           f'<a href="{DEPOT_ORIGINE}">{DEPOT_ORIGINE}</a>'))

    # L'adresse est celle que Xiom a choisi de publier. Le depot reste le
    # meilleur endroit pour signaler un defaut -- il garde une trace, et il est
    # lu par d'autres -- mais une adresse permet d'ecrire sans compte GitHub,
    # ce que tout le monde n'a pas.
    dedans.addWidget(_bloc(_("Écrire à l'auteur"),
                           f'<a href="mailto:{COURRIEL}">{COURRIEL}</a>'))

    credits = "<br>".join(f"{_(quoi)} : {qui}" for quoi, qui in CREDITS)
    dedans.addWidget(_bloc(_("Données et images"), credits))
    dedans.addStretch(1)

    defilant = QScrollArea()
    defilant.setWidget(contenu)
    defilant.setWidgetResizable(True)
    defilant.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    colonne.addWidget(defilant, 1)

    pied = QWidget()
    ligne = QVBoxLayout(pied)
    ligne.setContentsMargins(16, 0, 16, 12)
    fermer = QPushButton(_("Fermer"))
    fermer.clicked.connect(fen.accept)
    ligne.addWidget(fermer, 0, Qt.AlignmentFlag.AlignRight)
    colonne.addWidget(pied)
    fen.exec()
