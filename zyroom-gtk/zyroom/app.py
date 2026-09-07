"""Application GTK4 ZyRoom."""
from __future__ import annotations

import os

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Pango", "1.0")

from gi.repository import Gio, Gtk  # noqa: E402

from .window import MainWindow  # noqa: E402


# Sous Flatpak, l'application ne peut posséder sur D-Bus que le nom de son
# propre bac à sable : la variante dev tourne sous net.ryzom.zyroomgtk.dev et
# doit s'enregistrer sous ce nom, sinon GTK refuse de démarrer. FLATPAK_ID est
# posé par Flatpak ; hors bac à sable (sources, paquet .deb) on garde
# l'identifiant historique.
APP_ID = os.environ.get("FLATPAK_ID") or "net.ryzom.zyroomgtk"


class ZyroomApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._window = None

    def do_activate(self):
        if self._window is None:
            self._window = MainWindow(self)
        self._window.present()


def installer_journal_erreurs() -> None:
    """Note dans un fichier ce qui casse, faute de console.

    Une application lancée depuis le bureau n'a pas de terminal : une exception
    s'imprime sur une sortie que personne ne lit, et l'écran reste à moitié
    construit sans que rien ne le dise. Le crochet la range dans le journal,
    puis laisse la trace partir où elle allait.
    """
    import sys
    from .config import noter_erreur
    ancien = sys.excepthook

    def crochet(genre, valeur, trace):
        noter_erreur("exception non rattrapée", valeur)
        ancien(genre, valeur, trace)

    sys.excepthook = crochet


def main(argv=None) -> int:
    import sys
    installer_journal_erreurs()
    return ZyroomApp().run(argv if argv is not None else sys.argv)
