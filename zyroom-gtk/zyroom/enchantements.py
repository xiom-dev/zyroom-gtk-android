"""L'enchantement d'un objet : le sort qu'on y a gravé.

Une arme, un amplificateur, un bijou peuvent porter un sort — le jeu le montre
par une petite image dans le coin de l'icône, et par un nombre de charges de
sève. Le flux le décrit par ses **briques** : `bmpa01.sbrick` l'action,
`bmoetea04.sbrick` l'effet, puis les crédits qui en fixent le coût. Le pack du
client les nomme (« Missile Atysien », « Dégât d'Électricité »), et l'API sait
dessiner l'icône de chacune — la même qu'en jeu, en 24×24.

**Seul le flux personnage porte cette information.** Les coffres de guilde n'en
transmettent rien : vérifié sur 3138 objets de deux guildes, pas un nœud
`<enchantment>`. Ce n'est pas un oubli de lecture, c'est ce que l'API envoie ;
rien ne s'affichera donc sur un coffre de guilde, et il n'y a pas de repli à
inventer — deviner un enchantement serait pire que de n'en rien dire.
"""
from __future__ import annotations

#: Les briques de crédit : ce que le sort coûte en sève, en vie, en portée.
#: Elles complètent chaque sort et n'apprennent rien sur ce qu'il fait — c'est
#: du bruit dans une infobulle qui tient en deux lignes.
_PREFIXE_CREDIT = "bmc"


def enchante(item) -> bool:
    """Vrai si l'objet porte un sort."""
    return bool(getattr(item, "enchant_bricks", None))


def briques_parlantes(item) -> list[str]:
    """Les briques qui disent ce que le sort fait, crédits écartés."""
    return [brique for brique in item.enchant_bricks
            if not brique.startswith(_PREFIXE_CREDIT)]


def brique_icone(item) -> str:
    """La brique dont l'icône représente le sort, `''` s'il n'y en a pas.

    La première : c'est l'action — le missile, la guérison —, et c'est elle que
    le jeu dessine dans le coin de l'objet."""
    parlantes = briques_parlantes(item)
    return parlantes[0] if parlantes else ""


def resume(item, nommer) -> str:
    """« Missile Atysien · Dégât d'Électricité 5 », pour l'infobulle.

    `nommer` est la fonction qui rend un nom lisible depuis une fiche —
    `NameDb.name`. Sans pack chargé elle rend l'identifiant, ce qui reste plus
    parlant que rien : on voit au moins que l'objet est enchanté."""
    noms = []
    for brique in briques_parlantes(item):
        nom = (nommer(brique) or "").strip()
        if nom and nom not in noms:
            noms.append(nom)
    # Le sort porte l'effet deux fois : « Degat d'Electricite » puis « Degat
    # d'Electricite 5 », la seconde brique donnant le niveau. On ne garde que
    # la plus precise — celle dont l'autre n'est que le debut.
    return " · ".join(nom for nom in noms
                      if not any(autre is not nom and autre.startswith(nom)
                                 for autre in noms))
