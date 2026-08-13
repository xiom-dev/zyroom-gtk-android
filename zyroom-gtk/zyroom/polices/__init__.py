"""La police du titre, embarquée avec l'application.

**Pourquoi l'embarquer.** Pirata One n'est installée sur presque aucun système,
et le bac à sable de Flatpak ne voit pas les polices de l'hôte de toute façon :
sans ce fichier, le nom de l'application s'écrirait dans la police courante et
le portage ne ressemblerait plus au téléphone.

**Comment on la donne à Pango.** GTK n'a pas d'interface pour charger un fichier
de police ; c'est fontconfig qui en tient le catalogue, et il accepte qu'on lui
en ajoute une pour la durée du processus. On passe donc par sa bibliothèque
directement. Si quoi que ce soit échoue — pas de fontconfig, fichier absent — on
n'insiste pas : l'application s'écrit alors dans la police du système, ce qui
est laid mais pas cassé.

La SIL Open Font License veut que son texte voyage avec la police : il est à
côté, dans `OFL-PirataOne.txt`, et l'À propos nomme ses auteurs.
"""
import ctypes
import ctypes.util
import os

#: Le nom que Pango devra reconnaître, tel que la police se déclare elle-même.
FAMILLE = "Pirata One"

FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "pirata_one.ttf")


def charger() -> bool:
    """Ajoute la police au catalogue du processus. Rend vrai si c'est fait."""
    if not os.path.isfile(FICHIER):
        return False
    nom = ctypes.util.find_library("fontconfig")
    if not nom:
        return False
    try:
        fc = ctypes.CDLL(nom)
        fc.FcConfigAppFontAddFile.restype = ctypes.c_int
        fc.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        return bool(fc.FcConfigAppFontAddFile(None, FICHIER.encode("utf-8")))
    except (OSError, AttributeError):
        return False
