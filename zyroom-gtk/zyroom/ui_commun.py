"""Les deux outils que toutes les pages de l'interface s'échangent.

Ils vivaient dans `window.py`, qui les avait écrits pour lui-même. Depuis que
chaque écran a son module, les y laisser aurait obligé les pages à importer la
fenêtre — et la fenêtre importe les pages : chacune aurait attendu l'autre.
Ce module n'importe rien du portage, il ne peut donc rien boucler.
"""
from __future__ import annotations

import threading
import unicodedata

from gi.repository import GLib


def run_async(work, on_done):
    """Exécute `work()` dans un thread, puis `on_done(result, error)` sur le
    thread GTK."""
    def runner():
        try:
            res, err = work(), None
        except Exception as exc:  # noqa: BLE001 — on remonte l'erreur à l'UI
            res, err = None, exc
        GLib.idle_add(on_done, res, err)
    threading.Thread(target=runner, daemon=True).start()


def _norm(text: str) -> str:
    """Minuscule sans accents, pour une recherche tolérante."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()
