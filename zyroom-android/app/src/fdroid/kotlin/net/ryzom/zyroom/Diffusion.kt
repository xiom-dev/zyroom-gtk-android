package net.ryzom.zyroom

/**
 * Ce qui sépare les variantes de l'application.
 *
 * Version **F-Droid**, publique et construite par la logithèque.
 *
 * Elle masque le petit coffre, comme celle de la guilde, et **ne se met pas à
 * jour toute seule** : les règles d'inclusion de F-Droid refusent qu'une
 * application aille chercher un APK et le fasse installer. C'est le travail du
 * client F-Droid, qui vérifie la signature du dépôt avant de proposer quoi que
 * ce soit. Le manifeste de cette variante retire donc aussi la permission
 * d'installer des paquets, et elle n'embarque pas le `string_client.pack` du
 * jeu — les noms d'items s'importent depuis l'application.
 *
 * Le pendant de ce fichier vit dans `src/guilde/kotlin/` et `src/dev/kotlin/`.
 */
const val MASQUE_COFFRES = true

/** Voir `src/guilde/kotlin/` : F-Droid interdit qu'on se mette à jour soi-même. */
const val MISES_A_JOUR_INTEGREES = false
