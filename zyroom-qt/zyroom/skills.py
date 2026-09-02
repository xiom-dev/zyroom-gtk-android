"""L'arbre des compétences, déduit des codes.

Porté de `model/SkillTree.kt` du portage Android, où cette logique est déjà
couverte par des tests. Rien ne décrit la hiérarchie dans le flux de l'API :
c'est le code qui la porte, une compétence préfixant toutes celles qui en
descendent — `sf` « Combat », `sfm` « Mêlée », `sfms` « Manier épée ». L'ordre
alphabétique des codes est donc déjà celui de l'arbre, parents avant enfants.

Le calcul vit ici, hors de la fenêtre, pour être vérifiable sans écran.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Skill:
    """Une compétence : son code, son niveau, son avancement en pourcents.

    L'API donne l'avancement dans la partie décimale du niveau — `164.52` :
    niveau 164 atteint, un peu plus de la moitié du suivant. Une valeur entière
    ne dit rien de l'avancement, et vaut donc zéro ici."""
    code: str
    level: int
    progress: int = 0


@dataclass(frozen=True)
class Node:
    skill: Skill
    root: str          # racine de la branche : sf, sm, sh, sc
    parent: str | None
    depth: int
    has_children: bool


def parse_level(raw: str) -> tuple[int, int]:
    """« 164.52 » → (164, 52). Une valeur illisible vaut (0, 0)."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return 0, 0
    level = int(value)
    # Coupé à 99 : un arrondi ne doit pas afficher « 100 % » d'un niveau qui
    # n'est pas franchi.
    return level, min(99, max(0, round((value - level) * 100)))


def build_tree(skills: list[Skill]) -> list[Node]:
    """Range les compétences dans l'ordre de l'arbre, chacune avec sa place."""
    tree = []
    for skill in sorted(skills, key=lambda s: s.code):
        ancestors = [s for s in skills
                     if s.code != skill.code and skill.code.startswith(s.code)]
        tree.append(Node(
            skill=skill,
            root=min(ancestors, key=lambda s: len(s.code)).code if ancestors else skill.code,
            # Le parent est le plus proche des ancêtres, non le premier : l'API
            # saute parfois un échelon, et remonter à la racine décalerait tout
            # l'affichage.
            parent=max(ancestors, key=lambda s: len(s.code)).code if ancestors else None,
            depth=len(ancestors),
            has_children=any(s.code != skill.code and s.code.startswith(skill.code)
                             for s in skills),
        ))
    return tree


def visible(tree: list[Node], expanded: set[str]) -> list[Node]:
    """Ce qui se voit, `expanded` disant quelles compétences sont ouvertes.

    Une compétence n'apparaît que si son parent est ouvert **et lui-même
    visible** : replier une racine referme donc tout ce qu'elle contient, sans
    qu'on ait à oublier l'état des échelons du dessous — le rouvrir les retrouve
    comme on les avait laissés. Les codes étant triés, un parent est toujours
    décidé avant ses enfants : une seule passe suffit."""
    shown: set[str] = set()
    out = []
    for node in tree:
        if node.parent is None or (node.parent in shown and node.parent in expanded):
            shown.add(node.skill.code)
            out.append(node)
    return out


#: Le plafond du jeu : au-delà, une compétence ne monte plus.
NIVEAU_MAX = 250


def finished(tree: list[Node]) -> set[str]:
    """Les compétences finies — celles dont il n'y a plus rien à monter.

    Chaque échelon de l'arbre a son propre plafond : la racine vaut 20, la
    branche du dessous 50, puis 100, 150, 200, et 250 pour la feuille. Un père
    affiche donc 50 ou 100 alors que tout ce qu'il porte est au maximum, et rien
    ne montrait qu'il était terminé : c'est pourtant ce qu'on cherche en
    parcourant l'arbre.

    D'où la règle : une feuille est finie à 250, un père l'est quand tous ses
    enfants le sont. « Magie curative » plafonne à 100 et passe au vert dès que
    les quatre soins qu'elle porte sont au maximum, et le vert remonte jusqu'au
    titre de la branche quand la branche entière est faite.
    """
    children: dict[str, list[Node]] = {}
    for node in tree:
        children.setdefault(node.parent, []).append(node)

    done: set[str] = set()
    # Les codes d'un enfant sont plus longs que ceux de son père : les parcourir
    # du plus long au plus court décide les feuilles d'abord, en une passe.
    for node in sorted(tree, key=lambda n: len(n.skill.code), reverse=True):
        siens = children.get(node.skill.code, [])
        if (node.skill.level >= NIVEAU_MAX if not siens
                else all(n.skill.code in done for n in siens)):
            done.add(node.skill.code)
    return done


def niveau_atteint(tree: list[Node], code: str) -> int:
    """Le plus haut niveau de cette compétence et de tout ce qu'elle porte.

    **Chaque échelon a son propre plafond** : la racine vaut 20, la branche du
    dessous 50, puis 100, 150, 200, et 250 pour la feuille. « Créer bijoux »
    affiche donc 50 quand tout ce qu'elle porte est monté à 250 — le nombre au
    bout de la ligne dit le plafond de l'échelon, pas ce que le personnage sait
    faire, et il fallait déplier pour le savoir.

    On rend donc le plus haut niveau du sous-arbre. Une feuille rend le sien,
    ce qui ne change rien pour elle.
    """
    enfants: dict[str, list[Node]] = {}
    for node in tree:
        enfants.setdefault(node.parent, []).append(node)

    def plus_haut(nom: str, niveau: int) -> int:
        for fils in enfants.get(nom, ()):
            niveau = max(niveau, plus_haut(fils.skill.code, fils.skill.level))
        return niveau

    depart = next((n.skill.level for n in tree if n.skill.code == code), 0)
    return plus_haut(code, depart)


def branch_level(tree: list[Node], root: str) -> int:
    """Le niveau d'une branche : le plus haut de ses membres.

    Celui de la racine plafonne bas — Combat vaut 20 — et ne dit rien de ce que
    le personnage sait faire."""
    levels = [n.skill.level for n in tree if n.root == root]
    return max(levels) if levels else 0
