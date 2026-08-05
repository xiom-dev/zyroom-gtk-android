"""Application GTK4 ZyRoom."""
from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gio, Gtk  # noqa: E402

from .window import MainWindow  # noqa: E402


class ZyroomApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="net.ryzom.zyroomgtk",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self._window = None

    def do_activate(self):
        if self._window is None:
            self._window = MainWindow(self)
        self._window.present()


def main(argv=None) -> int:
    import sys
    return ZyroomApp().run(argv if argv is not None else sys.argv)
