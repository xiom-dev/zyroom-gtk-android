"""La fenêtre et ses pages se tiennent-elles debout, ensemble ?

**Deux erreurs de découpage ont traversé trois livraisons.** Une méthode
supprimée par mégarde — `_texte_du_rang` — faisait échouer le menu contextuel
du journal sur une `AttributeError` invisible, et une méthode définie deux fois
laissait croire qu'une correction était en place alors que la seconde copie,
inchangée, l'emportait. Python ne signale ni l'une ni l'autre.

Ce contrôle relit les fichiers et refuse les deux.

**Depuis que chaque écran a son module**, il les lit comme un seul ensemble :
`MainWindow` hérite des pages, donc une méthode appelée dans `window.py` peut
très bien être définie dans `page_meteo.py`. Les regarder séparément ferait
crier le contrôle à chaque découpage.

Ce même découpage ouvre un risque que le fichier unique n'avait pas : deux
pages qui définiraient la même méthode ne se signaleraient pas davantage —
l'ordre des bases déciderait, en silence, laquelle des deux s'exécute. Le
troisième contrôle ferme cette porte.
"""

import ast
import collections
import glob
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

#: Ce qui vient de GTK et n'a pas à être défini ici.
HERITE = ("get_", "set_", "add_", "remove_", "insert_", "queue_", "compute_",
          "observe_", "connect", "present", "close", "grab_", "activate",
          "emit", "lookup", "notify", "bind", "unbind", "measure", "query_",
          "pick", "snapshot", "allocate", "realize", "map", "show", "hide",
          "destroy", "is_", "maximize", "unmaximize", "fullscreen", "minimize")


def fichiers_interface():
    """La fenêtre et les écrans dont elle hérite, dans un ordre stable."""
    pages = sorted(glob.glob(os.path.join(RACINE, "zyroom", "page_*.py")))
    return [os.path.join(RACINE, "zyroom", "window.py")] + pages


def classes(chemin):
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    return [n for n in ast.walk(arbre) if isinstance(n, ast.ClassDef)]


def classes_de_la_fenetre(chemin):
    """Les seules classes que `MainWindow` rassemble en une.

    Dans `window.py`, c'est elle et elle seule : `LigneJournal` est un objet du
    modèle, qui a son `__init__` à elle sans rien écraser de personne. Dans les
    pages, tout ce qui s'y trouve est un mixin.
    """
    if os.path.basename(chemin) == "window.py":
        return [c for c in classes(chemin) if c.name == "MainWindow"]
    return classes(chemin)


def definis(classe):
    """Les noms qu'une classe pose : méthodes et attributs de classe."""
    noms = {f.name for f in classe.body if isinstance(f, ast.FunctionDef)}
    noms |= {c.targets[0].id for c in classe.body
             if isinstance(c, ast.Assign) and c.targets
             and isinstance(c.targets[0], ast.Name)}
    return noms


class Coherence(unittest.TestCase):

    def test_aucune_methode_definie_deux_fois(self):
        for fichier in fichiers_interface():
            for classe in classes(fichier):
                noms = [f.name for f in classe.body
                        if isinstance(f, ast.FunctionDef)]
                doublons = {n: c for n, c in collections.Counter(noms).items()
                            if c > 1}
                self.assertEqual({}, doublons,
                                 f"{os.path.basename(fichier)} — "
                                 f"{classe.name} : défini deux fois")

    def test_aucune_methode_appelee_sans_exister(self):
        tous = set()
        for fichier in fichiers_interface():
            for classe in classes(fichier):
                tous |= definis(classe)

        for fichier in fichiers_interface():
            for classe in classes(fichier):
                appels = {n.func.attr for n in ast.walk(classe)
                          if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute)
                          and isinstance(n.func.value, ast.Name)
                          and n.func.value.id == "self"}
                manquants = sorted(a for a in appels
                                   if a not in tous
                                   and not a.startswith(HERITE))
                self.assertEqual([], manquants,
                                 f"{os.path.basename(fichier)} — "
                                 f"{classe.name} : appelé mais absent")

    def test_aucune_page_n_ecrase_une_autre(self):
        """Deux écrans ne peuvent pas définir le même nom.

        `MainWindow` hérite de toutes les pages : deux méthodes de même nom et
        c'est l'ordre des bases qui tranche, sans un mot. Le jour où cela
        arrive, c'est la correction qu'on vient d'écrire qui ne s'exécute pas.
        """
        d_ou = collections.defaultdict(list)
        for fichier in fichiers_interface():
            for classe in classes_de_la_fenetre(fichier):
                for nom in definis(classe):
                    d_ou[nom].append(f"{os.path.basename(fichier)}:{classe.name}")
        partages = {n: ou for n, ou in d_ou.items() if len(ou) > 1}
        self.assertEqual({}, partages, "défini dans plusieurs classes à la fois")


if __name__ == "__main__":
    unittest.main()
