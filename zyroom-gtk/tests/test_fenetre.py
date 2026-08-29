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


class FauxContenant:
    def __init__(self, capacite, volume):
        self.capacity = capacite
        self.total_volume = volume


class LeRemplissageDansLeMenu(unittest.TestCase):
    """Le taux collé en fin de ligne du menu des coffres.

    Du calcul pur : pas besoin d'écran, ce test tourne partout.
    """

    def taux(self, capacite, volume) -> str:
        from zyroom.window import MainWindow
        return MainWindow._remplissage(FauxContenant(capacite, volume))

    def test_le_taux_se_colle_en_fin_de_ligne(self):
        self.assertEqual(" (63%)", self.taux(300, 189.4))
        self.assertEqual(" (0%)", self.taux(300, 0))
        self.assertEqual(" (100%)", self.taux(300, 300))

    def test_sans_capacite_connue_on_n_affiche_rien(self):
        """« (0%) » ferait croire à un coffre vide, ce qu'il n'est pas.

        L'API ne donne pas la capacité de tous les contenants, et un menu qui
        annonce vide un coffre plein est pire qu'un menu qui se tait.
        """
        self.assertEqual("", self.taux(0, 50))
        self.assertEqual("", self.taux(-1, 50))


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

    def test_la_fenetre_des_cles_se_monte(self):
        """Les dialogues aussi masquent `_`, et personne ne les montait.

        Le cas réel qui a motivé ce test : `def update_hint(*_)` rend `_` —
        la fonction de traduction — locale à la fonction, et le premier
        `_("…")` de son corps appelle alors un tuple. Même piège que
        `_build_meteo_page`, mais dans une fenêtre que le test d'à côté
        n'ouvre pas : la construction des pages ne dit rien des dialogues,
        qui ne se montent qu'au clic.

        On monte donc les trois : la fenêtre des clés, le remplacement d'une
        clé, la confirmation de retrait. Sans réseau — rien n'est validé ici,
        seulement construit.
        """
        from zyroom.window import KIND_CHARACTER, MainWindow

        ennuis = []
        app = Gtk.Application(application_id="net.ryzom.zyroomgtk.test.cles")

        def activer(_application):
            try:
                fenetre = MainWindow(application=app)
                fenetre._char_store.save("689325", "c" + "0" * 40, "Xiom",
                                         "atys", "La Lune Eternelle")
                fenetre._on_add_clicked(None)
                cles = [f for f in Gtk.Window.list_toplevels()
                        if f.get_title() == "Clés API"]
                self.assertTrue(cles, "la fenêtre des clés ne s'est pas ouverte")

                entree = dict(fenetre._char_store.entries()[0])
                page = Gtk.Box()
                fenetre._dialogue_changer_cle(entree, KIND_CHARACTER,
                                              fenetre._char_store, page, cles[0])
                self.assertTrue(
                    [f for f in Gtk.Window.list_toplevels()
                     if f.get_title() == "Remplacer la clé"],
                    "le dialogue de remplacement ne s'est pas ouvert")

                fenetre._confirmer_retrait(entree, fenetre._char_store,
                                           page, cles[0])
            except Exception as souci:      # noqa: BLE001 — remontée telle quelle
                ennuis.append(souci)
            finally:
                for f in list(Gtk.Window.list_toplevels()):
                    f.destroy()
                app.quit()

        app.connect("activate", activer)
        app.run([])
        if ennuis:
            raise ennuis[0]

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
