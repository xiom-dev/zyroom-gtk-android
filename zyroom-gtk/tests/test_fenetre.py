"""La fenêtre se construit-elle ? Le seul test qui monte l'interface entière.

Rien de subtil ici, et c'est justement ce qui manquait : tous les autres tests
appellent des fonctions isolées, si bien qu'une méthode de construction qui
lève passe inaperçue — alors qu'elle laisse une application qui ne démarre
pas du tout.

Le cas réel qui a motivé ce fichier : une boucle `for _ in range(...)` dans
`_build_meteo_page` a rendu `_` — la fonction de traduction — locale à la
méthode, et chaque `_("…")` de l'écran météo levait une UnboundLocalError dès
le lancement. Les 154 tests d'alors passaient tous.

Le test s'installe un HOME jetable : sans personnage ni guilde configurés, la
fenêtre se monte sans rien demander au réseau. Sans écran, il se passe.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gi                                                        # noqa: E402
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk                                    # noqa: E402


def _ecran() -> bool:
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    return bool(Gtk.init_check())


ECRAN = _ecran()


@unittest.skipUnless(ECRAN, "aucun écran : il n'y a rien à construire")
class LaFenetreSeMonte(unittest.TestCase):

    def setUp(self):
        # Un HOME jetable : ni entité à charger, ni synchro à lancer, et rien
        # d'écrit dans la configuration de celui qui lance les tests.
        self._jetable = tempfile.TemporaryDirectory()
        self._anciennes = {}
        for variable in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
            self._anciennes[variable] = os.environ.get(variable)
            os.environ[variable] = os.path.join(self._jetable.name,
                                                variable.lower())

    def tearDown(self):
        for variable, valeur in self._anciennes.items():
            if valeur is None:
                os.environ.pop(variable, None)
            else:
                os.environ[variable] = valeur
        self._jetable.cleanup()

    def test_toutes_les_pages_se_construisent(self):
        """Monter la fenêtre, c'est appeler chaque `_build_*_page`.

        L'exception est renvoyée telle quelle : le message d'origine et sa
        pile disent quelle page a cassé, ce qu'un simple « faux » ne dirait
        pas."""
        from zyroom.window import MainWindow

        ennuis = []
        app = Gtk.Application(application_id="net.ryzom.zyroomgtk.test")

        def activer(_application):
            try:
                fenetre = MainWindow(application=app)
                # Le bloc « ce qui sort » a une colonne par zone des Primes.
                self.assertEqual(MainWindow.COLONNES_POP,
                                 len(fenetre._meteo_pop_colonnes))
                fenetre.destroy()
            except Exception as exception:       # remontée après la boucle
                ennuis.append(exception)
            app.quit()

        app.connect("activate", activer)
        app.run([])
        if ennuis:
            raise ennuis[0]


if __name__ == "__main__":
    unittest.main()
