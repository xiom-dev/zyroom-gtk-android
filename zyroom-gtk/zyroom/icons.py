"""Cache disque + téléchargement concurrent des icônes d'items.

Reprend le principe de l'original : un pool de threads télécharge les icônes en
parallèle (cf. option ThreadCount) tandis que le résultat est renvoyé au thread
GTK via GLib.idle_add. Les fichiers de cache portent le même nom que dans zyRoom
d'origine, ce qui permet de réutiliser un cache existant.
"""
from __future__ import annotations

import os
import threading
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
        GLib.idle_add(callback, self._telecharger(self.cached_path(item),
                                                  lambda: ryzom_api.fetch_item_icon(item)))

    def _telecharger(self, path: str, chercher) -> str | None:
        """Le fichier de cache, en le téléchargeant s'il manque. `None` en cas d'échec.

        **Un temporaire par appel.** Une grille montre le même item plusieurs
        fois — vingt-cinq doublons dans un coffre de deux cents —, et autant de
        threads partaient alors sur le même `.part` : le premier le renommait,
        les autres ne le retrouvaient plus, échouaient sur ce `os.replace`, et
        rendaient `None`. L'appelant affichait son icône générique alors que
        l'image était bel et bien téléchargée, dans le cache, à côté.

        D'où aussi le second regard sur le fichier final avant d'abandonner :
        quand deux téléchargements se croisent, celui qui perd n'a pas échoué,
        il est arrivé deuxième."""
        try:
            if not (os.path.isfile(path) and os.path.getsize(path) > 0):
                data = chercher()
                tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.part"
                try:
                    with open(tmp, "wb") as fh:
                        fh.write(data)
                    os.replace(tmp, path)
                finally:
                    # Un temporaire abandonne en route ne doit pas rester : le
                    # cache d'icones n'est jamais nettoye autrement.
                    if os.path.isfile(tmp):
                        os.unlink(tmp)
            return path
        except Exception:                               # noqa: BLE001
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                return path                             # un autre l'a ecrit
            return None

    def request_brique(self, sheet: str, callback) -> None:
        """Demande l'icône d'une brique de sort (l'enchantement d'un objet).

        Même pool et même cache que les items : quelques dizaines d'objets
        enchantés dans un inventaire, et souvent le même sort sur plusieurs."""
        if not sheet:
            GLib.idle_add(callback, None)
            return
        self._executor.submit(self._work_brique, sheet, callback)

    def _work_brique(self, sheet: str, callback) -> None:
        path = os.path.join(self._dir, f"brique-{sheet}.png")
        GLib.idle_add(callback, self._telecharger(
            path, lambda: ryzom_api.fetch_brique_icon(sheet)))

    def request_emblem(self, icon_id: str, callback, size: str = "s") -> None:
        """Demande l'emblème d'une guilde, dessiné par l'API à partir de son
        identifiant.

        Même cache et même thread que les icônes d'items : un tableau des
        avant-postes en demande une trentaine d'un coup, et les redemander à
        chaque affichage ferait clignoter la fenêtre."""
        if not icon_id:
            GLib.idle_add(callback, None)
            return
        self._executor.submit(self._work_emblem, icon_id, size, callback)

    def _work_emblem(self, icon_id: str, size: str, callback) -> None:
        path = os.path.join(self._dir, f"guild-{icon_id}-{size}.png")
        GLib.idle_add(callback, self._telecharger(
            path, lambda: ryzom_api.fetch_url(
                ryzom_api.guild_icon_url(icon_id, size))))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
