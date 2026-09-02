"""Cache disque + téléchargement concurrent des icônes d'objets.

Reprend le principe de l'original : un pool de threads télécharge les icônes
en parallèle tandis que le résultat revient au thread de l'interface. Les
fichiers de cache portent le même nom que dans le zyRoom d'origine — un cache
existant, y compris celui de ZyRoom-GTK, se réutilise donc tel quel.

**Le seul vrai écart avec la version GTK.** Une icône se télécharge dans un
thread, mais une image ne se pose que depuis le thread de l'interface : les
deux boîtes à outils l'exigent, aucune n'est sûre en multi-thread. GTK offrait
`GLib.idle_add`, qui dépose un appel dans la boucle principale. Qt n'a pas
d'équivalent direct, mais il a mieux : un signal connecté en
`QueuedConnection` traverse les threads et se déclenche sur celui qui possède
l'objet receveur. Le relais ci-dessous n'est que cela — un `idle_add` écrit en
Qt, en cinq lignes.

**Pourquoi une classe de relais plutôt qu'un signal par icône.** Une grille de
coffre en demande jusqu'à quatre cents : autant d'objets Qt à créer, à
connecter et à détruire. Un seul relais, partagé, porte le rappel dans son
propre signal.
"""
from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, Qt, Signal

from . import ryzom_api
from .config import icon_cache_dir
from .models import ItemInfo


class _Relais(QObject):
    """Fait exécuter un rappel sur le thread de l'interface."""

    arrive = Signal(object, object)          # rappel, resultat

    def __init__(self) -> None:
        super().__init__()
        # QueuedConnection : le rappel ne s'execute pas dans le thread qui
        # emet, mais dans celui qui possede ce relais -- l'interface.
        self.arrive.connect(self._livrer, Qt.ConnectionType.QueuedConnection)

    @staticmethod
    def _livrer(rappel, resultat) -> None:
        rappel(resultat)


class ChargeurIcones:
    def __init__(self, max_workers: int = 8) -> None:
        self._dir = icon_cache_dir()
        self._executor = ThreadPoolExecutor(max_workers=max_workers,
                                            thread_name_prefix="icone")
        self._relais = _Relais()

    def chemin_cache(self, item: ItemInfo) -> str:
        return os.path.join(self._dir, item.cache_filename)

    def demander(self, item: ItemInfo, rappel) -> None:
        """Demande l'icône d'un objet.

        `rappel(chemin_ou_None)` est appelé sur le thread de l'interface :
        le chemin si l'icône est disponible, `None` en cas d'échec.
        """
        self._executor.submit(self._travail, item, rappel)

    def _travail(self, item: ItemInfo, rappel) -> None:
        chemin = self._telecharger(self.chemin_cache(item),
                                   lambda: ryzom_api.fetch_item_icon(item))
        self._relais.arrive.emit(rappel, chemin)

    def _telecharger(self, path: str, chercher) -> str | None:
        """Le fichier de cache, en le téléchargeant s'il manque. `None` si échec.

        **Un temporaire par appel.** Une grille montre le même objet plusieurs
        fois — vingt-cinq doublons dans un coffre de deux cents —, et autant de
        threads partaient alors sur le même `.part` : le premier le renommait,
        les autres ne le retrouvaient plus et rendaient `None`. L'appelant
        affichait son icône générique alors que l'image était bel et bien dans
        le cache, à côté.

        D'où aussi le second regard sur le fichier final avant d'abandonner :
        quand deux téléchargements se croisent, celui qui perd n'a pas échoué,
        il est arrivé deuxième.
        """
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

    def demander_brique(self, sheet: str, rappel) -> None:
        """Demande l'icône d'une brique de sort (l'enchantement d'un objet).

        Même pool et même cache que les objets : quelques dizaines d'objets
        enchantés dans un inventaire, et souvent le même sort sur plusieurs.
        """
        if not sheet:
            self._relais.arrive.emit(rappel, None)
            return
        self._executor.submit(self._travail_brique, sheet, rappel)

    def _travail_brique(self, sheet: str, rappel) -> None:
        chemin = os.path.join(self._dir, f"brique-{sheet}.png")
        resultat = self._telecharger(
            chemin, lambda: ryzom_api.fetch_brique_icon(sheet))
        self._relais.arrive.emit(rappel, resultat)

    def demander_embleme(self, icon_id: str, rappel, taille: str = "s") -> None:
        """Demande l'emblème d'une guilde, dessiné par l'API d'après son
        identifiant.

        Même pool et même cache que les icônes d'objets : un tableau des
        avant-postes en demande une trentaine d'un coup, et les redemander à
        chaque affichage ferait clignoter la fenêtre.
        """
        if not icon_id:
            self._relais.arrive.emit(rappel, None)
            return
        self._executor.submit(self._travail_embleme, icon_id, taille, rappel)

    def _travail_embleme(self, icon_id: str, taille: str, rappel) -> None:
        chemin = os.path.join(self._dir, f"guild-{icon_id}-{taille}.png")
        resultat = self._telecharger(
            chemin, lambda: ryzom_api.fetch_url(
                ryzom_api.guild_icon_url(icon_id, taille)))
        self._relais.arrive.emit(rappel, resultat)

    def arreter(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
