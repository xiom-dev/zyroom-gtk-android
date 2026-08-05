"""Cache disque + téléchargement concurrent des icônes d'items.

Reprend le principe de l'original : un pool de threads télécharge les icônes en
parallèle (cf. option ThreadCount) tandis que le résultat est renvoyé au thread
GTK via GLib.idle_add. Les fichiers de cache portent le même nom que dans zyRoom
d'origine, ce qui permet de réutiliser un cache existant.
"""
from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

from gi.repository import GLib

from . import ryzom_api
from .config import icon_cache_dir
from .models import ItemInfo


class IconLoader:
    def __init__(self, max_workers: int = 8) -> None:
        self._dir = icon_cache_dir()
        self._executor = ThreadPoolExecutor(max_workers=max_workers,
                                             thread_name_prefix="icon")

    def cached_path(self, item: ItemInfo) -> str:
        return os.path.join(self._dir, item.cache_filename)

    def request(self, item: ItemInfo, callback) -> None:
        """Demande l'icône d'un item. `callback(path_or_None)` est appelé sur le
        thread principal GTK : `path` si l'icône est disponible, `None` en cas
        d'échec."""
        self._executor.submit(self._work, item, callback)

    def _work(self, item: ItemInfo, callback) -> None:
        path = self.cached_path(item)
        result = path
        try:
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                data = ryzom_api.fetch_item_icon(item)
                tmp = path + ".part"
                with open(tmp, "wb") as fh:
                    fh.write(data)
                os.replace(tmp, path)
        except Exception:
            result = None
        # Retour sur le thread GTK
        GLib.idle_add(callback, result)

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
