"""Ce que les deux cartes ont en commun.

Deux écrans dessinent Atys au pinceau de Cairo : « Perdu ? », qui pose les
bêtes du joueur, et les gisements, qui posent les points d'une matière. Ils ne
partagent pas leur code — l'un groupe des bêtes voisines, l'autre cadre une
zone — mais bien quatre réglages, et les laisser en double les aurait laissés
diverger : un zoom qui s'arrête à six d'un côté et à huit de l'autre, sur la
même carte, se remarque tout de suite.

C'est un mixin : `MainWindow` en hérite, et `self.ZOOM_MAX` se lit des deux
côtés comme avant.
"""
from __future__ import annotations


class CartesCommunes:
    """Les réglages que « Perdu ? » et les gisements partagent."""

    #: Le rouge du point. Il n'existe nulle part ailleurs sur la carte à ce ton.
    POINT = (1.0, 0.18, 0.18)

    #: Le gris d'un gisement qui ne sort pas en ce moment.
    #:
    #: Gris et non effacé : le montrer dit « ici, mais pas maintenant », ce
    #: qu'une carte amputée ne dirait pas. Assez clair pour rester visible sur
    #: les zones sombres d'Atys, assez terne pour qu'on ne le confonde jamais
    #: avec le rouge en un coup d'œil.
    POINT_INACTIF = (0.58, 0.58, 0.60)

    #: En deçà de cette distance à l'écran, deux points n'en font qu'un.
    #:
    #: Quarante pixels : de quoi séparer deux troupeaux laissés dans deux
    #: régions, sans écrire quatre fois le même nom pour quatre mektoubs
    #: attachés ensemble.
    SEUIL_GROUPE = 40.0

    #: Jusqu'où l'agrandissement va. Au-delà, on n'ajoute plus que du flou.
    ZOOM_MAX = 6.0

    #: Un cran de molette. On agrandit de ce facteur, et on rapetisse de son
    #: **inverse** : avec 1,1 et 0,9, trois crans dans un sens puis trois dans
    #: l'autre laissaient la carte à 97 % de sa taille, et on ne retrouvait
    #: jamais tout à fait la vue qu'on avait.
    PAS_ZOOM = 1.1
