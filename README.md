# ZyRoom — portages libres pour Linux et Android

**Licence : GNU AGPLv3 ou ultérieure — le texte complet est dans le fichier
[`LICENSE`](LICENSE) à la racine du dépôt.**

Outils compagnons du MMORPG **Ryzom** : consulter hors-ligne les inventaires de
ses personnages et des coffres de sa guilde, via l'API web officielle.

Ce dépôt porte deux applications, écrites à partir de la même spécification —
le **zyRoom** de Misugi, en Delphi pour Windows.

| dossier | ce que c'est |
|---|---|
| [`zyroom-gtk/`](zyroom-gtk/) | l'application de bureau, en Python et GTK4 (Debian et dérivées, Flatpak) |
| [`zyroom-android/`](zyroom-android/) | l'application pour téléphone, en Kotlin et Jetpack Compose |

Chacune a son README : ce qu'elle sait faire, comment la construire, comment
l'installer.

## Télécharger

Les applications prêtes à installer sont dans les
[**Releases**](../../releases) — un bundle Flatpak pour le bureau, un APK pour
le téléphone. Elles n'y sont pas versionnées dans l'historique : un binaire pèse
des mégaoctets et git en garderait chaque version pour toujours.

## Deux variantes de chaque application

| variante | pour qui | différence |
|---|---|---|
| ordinaire | la guilde | le contenu d'un coffre réservé n'est pas affiché |
| `(dev)` | le mainteneur | tout est affiché |

Elles portent des identifiants distincts et s'installent côte à côte.

## Clés d'API

**Aucune clé n'est livrée avec les applications.** Chacun ajoute les siennes au
premier démarrage : celle de sa guilde, et la sienne pour ses propres
inventaires. Elles se créent sur https://api.ryzom.com — modules `C01 C04 C05
C06 A01 A03` pour un personnage, `G01 G02 G03` pour une guilde.

Une clé donne un accès en lecture aux inventaires qu'elle couvre : elle se
traite comme un mot de passe, et n'a rien à faire dans un dépôt.

## Licence

**GNU AGPLv3 ou ultérieure** (`AGPL-3.0-or-later`), comme le zyRoom d'origine
dont ces portages dérivent — https://github.com/misugi/zyroom. Le texte complet
est dans le [`LICENSE`](LICENSE) à la racine, et repris dans le `LICENSE.md` de
chaque projet.

Ces applications sont des **œuvres dérivées** : elles traduisent les algorithmes
du zyRoom Delphi de Misugi. L'AGPL impose qu'elles gardent sa licence — on ne
peut ni la remplacer par la GPL, dont elle se distingue par l'article 13, ni
effacer la paternité d'origine.

- zyRoom original : © Misugi
- portages GTK et Android : © 2026 Xiom

En clair : ces applications sont libres, et quiconque en reçoit une copie a
droit au code source correspondant, sous la même licence.
