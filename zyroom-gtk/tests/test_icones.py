"""Le cache d'icônes tient-il quand le même item est demandé plusieurs fois ?

Le cas réel qui a motivé ce fichier : dans un coffre, vingt-cinq icônes sur
deux cents sont demandées deux ou trois fois — autant d'exemplaires du même
objet. Les threads partaient tous sur le même fichier temporaire ; le premier
le renommait, les autres ne le retrouvaient plus et rendaient `None`. Trois
cases affichaient l'icône générique de GTK alors que l'image était dans le
cache, à côté.
"""

import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["XDG_CACHE_HOME"] = tempfile.mkdtemp()

import gi
gi.require_version("Gtk", "4.0")

from zyroom import icons, ryzom_api
from zyroom.models import ItemInfo

# Un PNG minuscule mais valide, pour ne rien telecharger.
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6300010000050001"
    "0d0a2db40000000049454e44ae426082")


class MemeItemPlusieursFois(unittest.TestCase):

    def setUp(self):
        # Les callbacks reviennent normalement par la boucle GTK ; ici on les
        # appelle sur place, le test n'en fait pas tourner.
        self._idle = icons.GLib.idle_add
        self._fetch = ryzom_api.fetch_item_icon
        icons.GLib.idle_add = lambda f, *a: f(*a)

        def lent(_item):
            time.sleep(0.1)           # de quoi faire se croiser les threads
            return PNG
        ryzom_api.fetch_item_icon = lent

    def tearDown(self):
        icons.GLib.idle_add = self._idle
        ryzom_api.fetch_item_icon = self._fetch

    def test_toutes_les_demandes_recoivent_l_icone(self):
        loader = icons.IconLoader()
        item = ItemInfo(sheet="test.sitem", quality=250, stack=1)
        recus, verrou = [], threading.Lock()

        def callback(path):
            with verrou:
                recus.append(path)
            return False

        for _ in range(8):
            loader.request(item, callback)
        loader.shutdown()
        for _ in range(50):           # on attend les huit reponses
            if len(recus) == 8:
                break
            time.sleep(0.05)

        self.assertEqual(8, len(recus))
        self.assertTrue(all(recus), "une demande a rendu None : l'appelant "
                                    "affiche alors l'icône générique")

    def test_aucun_temporaire_ne_traine(self):
        """Le cache d'icônes n'est jamais nettoyé : rien ne doit y rester."""
        loader = icons.IconLoader()
        item = ItemInfo(sheet="reste.sitem", quality=100, stack=1)
        for _ in range(4):
            loader.request(item, lambda _p: False)
        loader.shutdown()
        time.sleep(0.6)
        dossier = os.path.dirname(loader.cached_path(item))
        self.assertEqual([], [f for f in os.listdir(dossier) if ".part" in f])


if __name__ == "__main__":
    unittest.main()
