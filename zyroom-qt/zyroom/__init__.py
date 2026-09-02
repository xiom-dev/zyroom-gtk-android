"""ZyRoom Qt — portage Qt/Python de l'application Windows zyRoom (Delphi).

Outil compagnon pour le MMORPG Ryzom : consultation hors-ligne des inventaires
de personnages et des coffres de guilde, via l'API web officielle.

Ce portage partage son noyau métier avec ZyRoom-GTK — les modules qui parlent
à l'API, calculent les volumes et tiennent les journaux sont les mêmes fichiers,
recopiés par `outils/sync-noyau.sh`. Ce qui change ici, c'est l'interface : Qt
à la place de GTK4, et donc Windows en plus de Linux.

Portage sous licence GNU AGPLv3, d'après le projet original de Misugi
(https://github.com/misugi/zyroom).
"""

__version__ = "1.2.0"

#: Le numero que la mise a jour compare, et lui seul. Un nom se compare mal --
#: "0.10" vient apres "0.9" pour nous, avant pour un tri de chaines. Il croit
#: d'une unite a chaque livraison, comme le versionCode d'Android, et c'est ce
#: meme entier que `version.json` annonce sur la page de telechargement.
__version_code__ = 12
