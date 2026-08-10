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


def main(argv=None) -> int:
    import sys
    return ZyroomApp().run(argv if argv is not None else sys.argv)
