"""Le fichier de la fenêtre se tient-il debout ?

**Deux erreurs de découpage ont traversé trois livraisons.** Une méthode
supprimée par mégarde — `_texte_du_rang` — faisait échouer le menu contextuel
du journal sur une `AttributeError` invisible, et une méthode définie deux fois
laissait croire qu'une correction était en place alors que la seconde copie,
inchangée, l'emportait. Python ne signale ni l'une ni l'autre.

Ce contrôle relit le fichier et refuse les deux.
"""

import ast
import collections
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


def classes(chemin):
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    return [n for n in ast.walk(arbre) if isinstance(n, ast.ClassDef)]


class Coherence(unittest.TestCase):

    FICHIERS = ("zyroom/window.py",)

    def test_aucune_methode_definie_deux_fois(self):
        for fichier in self.FICHIERS:
            for classe in classes(os.path.join(RACINE, fichier)):
                noms = [f.name for f in classe.body
                        if isinstance(f, ast.FunctionDef)]
                doublons = {n: c for n, c in collections.Counter(noms).items()
                            if c > 1}
                self.assertEqual({}, doublons,
                                 f"{fichier} — {classe.name} : défini deux fois")

    def test_aucune_methode_appelee_sans_exister(self):
        for fichier in self.FICHIERS:
            for classe in classes(os.path.join(RACINE, fichier)):
                definis = {f.name for f in classe.body
                           if isinstance(f, ast.FunctionDef)}
                definis |= {c.targets[0].id for c in classe.body
                            if isinstance(c, ast.Assign) and c.targets
                            and isinstance(c.targets[0], ast.Name)}
                appels = {n.func.attr for n in ast.walk(classe)
                          if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute)
                          and isinstance(n.func.value, ast.Name)
                          and n.func.value.id == "self"}
                manquants = sorted(a for a in appels
                                   if a not in definis
                                   and not a.startswith(HERITE))
                self.assertEqual([], manquants,
                                 f"{fichier} — {classe.name} : appelé mais absent")


if __name__ == "__main__":
    unittest.main()
