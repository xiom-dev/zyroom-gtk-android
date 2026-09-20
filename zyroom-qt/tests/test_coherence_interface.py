#!/usr/bin/env python3
"""L'interface s'appelle-t-elle elle-meme sans se tromper de nom ?

**C'est arrive, et une livraison entiere l'a porte.** « Qt : la copie du
journal et la recherche appelaient des noms non importes » -- un
`AttributeError` qui n'apparait qu'au clic, dans un menu contextuel que
personne n'ouvre en essayant l'application cinq minutes. Le portage GTK a son
controle depuis ces deux memes accidents ; celui-ci est le sien.

Rien n'est importe ni execute : on relit les fichiers. Un essai qui demanderait
PySide6 et un `QApplication` ne tournerait pas partout, et surtout pas la ou
l'on veut justement savoir si le code se tient -- sur une machine qui n'a pas
l'environnement complet.

**Comment on distingue nos methodes de celles de Qt.** Les notres sont en
francais, mot a mot separe par des soulignes ; celles de Qt sont en
`camelCase` -- `setLayout`, `addWidget`, `resizeEvent`. On ne regarde donc que
les appels en minuscules, et Qt reste dehors sans qu'il faille en tenir la
liste.
"""
import ast
import collections
import glob
import os
import re
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: Les fichiers de l'interface : la fenetre, ses pages, la carte commune.
FICHIERS = sorted(
    glob.glob(os.path.join(RACINE, "zyroom", "fenetre.py"))
    + glob.glob(os.path.join(RACINE, "zyroom", "page_*.py"))
    + glob.glob(os.path.join(RACINE, "zyroom", "carte_widget.py"))
    + glob.glob(os.path.join(RACINE, "zyroom", "cles.py"))
    + glob.glob(os.path.join(RACINE, "zyroom", "options.py"))
    + glob.glob(os.path.join(RACINE, "zyroom", "detail.py")))

#: Ce qui vient de Qt s'ecrit en camelCase, et n'a pas a etre defini ici.
QT = re.compile(r"[a-z]+[A-Z]")

#: Le peu de noms en minuscules qui viennent quand meme d'ailleurs : de Qt,
#: de Python, ou poses sur un objet qui n'est pas nous. Qt ecrit presque tout
#: en camelCase, mais pas ses accesseurs les plus courts -- width(), height(),
#: pos(), font() --, et ceux-la, il faut bien les nommer.
DEHORS = {"connect", "emit", "disconnect", "close", "show", "hide", "update",
          "repaint", "raise_", "exec", "accept", "reject", "done", "start",
          "stop", "quit", "append", "add", "get", "join", "keys", "items",
          "values", "format", "strip", "lower", "upper", "split", "read",
          "write", "sort", "index", "count", "copy", "clear", "pop", "remove",
          "insert", "extend", "run", "cancel", "wait", "release", "acquire",
          # Les accesseurs de QWidget et consorts.
          "width", "height", "x", "y", "size", "pos", "rect", "font",
          "palette", "style", "parent", "children", "layout", "geometry",
          "cursor", "window", "text", "title", "value", "icon", "move",
          "resize", "scroll", "grab", "render", "activate", "click",
          "setdefault", "widget", "item", "row", "column", "columns",
          "toggle", "scale", "translate", "rotate", "save", "restore",
          "device", "depth", "state", "mask", "region", "screen"}


def classes_du_fichier(chemin):
    arbre = ast.parse(open(chemin, encoding="utf-8").read())
    return [n for n in ast.walk(arbre) if isinstance(n, ast.ClassDef)]


def toutes_les_classes():
    """{nom: noeud} pour toutes les classes de l'interface."""
    trouvees = {}
    for chemin in FICHIERS:
        for classe in classes_du_fichier(chemin):
            trouvees[classe.name] = (os.path.basename(chemin), classe)
    return trouvees


def noms_definis(classe, connues, vus=None):
    """Ce qu'une classe pose, en remontant ses bases a nous.

    Une page qui herite d'une autre page du projet -- `CarteGisements` vient de
    `CarteAtys` -- dispose de ses methodes : les oublier ferait crier le
    controle a tort.
    """
    vus = vus or set()
    if classe.name in vus:
        return set()              # une boucle d'heritage n'arrivera pas, mais
    vus.add(classe.name)          # autant ne pas y tourner si elle arrivait
    noms = {f.name for f in classe.body
            if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}
    noms |= {c.targets[0].id for c in classe.body
             if isinstance(c, ast.Assign) and c.targets
             and isinstance(c.targets[0], ast.Name)}
    # Ce que __init__ et les autres posent sur self : self._page = ... est un
    # attribut, pas une methode, mais il s'appelle parfois comme une fonction
    # (un lambda range dans un attribut, par exemple).
    for noeud in ast.walk(classe):
        if isinstance(noeud, ast.Attribute) and not isinstance(noeud.ctx, ast.Load) \
                and isinstance(noeud.value, ast.Name) and noeud.value.id == "self":
            noms.add(noeud.attr)
    for base in classe.bases:
        if isinstance(base, ast.Name) and base.id in connues:
            noms |= noms_definis(connues[base.id][1], connues, vus)
    return noms


class Coherence(unittest.TestCase):

    def test_il_y_a_bien_des_fichiers_a_controler(self):
        """Un controle qui ne regarde rien passe toujours."""
        self.assertGreaterEqual(len(FICHIERS), 8, FICHIERS)

    def test_aucune_methode_definie_deux_fois(self):
        """La seconde copie l'emporte, et la correction qu'on vient d'ecrire dort."""
        for chemin in FICHIERS:
            for classe in classes_du_fichier(chemin):
                noms = [f.name for f in classe.body
                        if isinstance(f, ast.FunctionDef)]
                doublons = {n: c for n, c in collections.Counter(noms).items()
                            if c > 1}
                self.assertEqual({}, doublons,
                                 f"{os.path.basename(chemin)} — {classe.name}")

    def test_aucune_methode_appelee_sans_exister(self):
        connues = toutes_les_classes()
        for chemin in FICHIERS:
            for classe in classes_du_fichier(chemin):
                definis = noms_definis(classe, connues)
                appels = {n.func.attr for n in ast.walk(classe)
                          if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute)
                          and isinstance(n.func.value, ast.Name)
                          and n.func.value.id == "self"}
                manquants = sorted(a for a in appels
                                   if a not in definis
                                   and not QT.search(a)
                                   and a not in DEHORS)
                self.assertEqual([], manquants,
                                 f"{os.path.basename(chemin)} — {classe.name} :"
                                 " appelé mais absent")


if __name__ == "__main__":
    unittest.main()
