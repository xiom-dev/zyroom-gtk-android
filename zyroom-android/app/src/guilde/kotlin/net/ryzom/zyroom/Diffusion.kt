package net.ryzom.zyroom

/**
 * Ce qui sépare les variantes de l'application.
 *
 * Version **guilde**, celle qu'on distribue depuis la page GitHub : le contenu
 * du petit coffre n'est pas montré — le coffre lui-même reste dans la liste,
 * mais vide —, et l'application va chercher ses propres mises à jour, faute de
 * logithèque pour le faire à sa place.
 *
 * Le pendant de ce fichier vit dans `src/dev/kotlin/` et `src/fdroid/kotlin/`.
 */
const val MASQUE_COFFRES = true

/**
 * Vrai si l'application sait se mettre à jour toute seule.
 *
 * Elle interroge alors `version.json`, télécharge l'APK et le présente au
 * système, qui demande confirmation. Faux pour la variante F-Droid, dont la
 * logithèque s'en charge et dont les règles l'interdisent.
 */
const val MISES_A_JOUR_INTEGREES = true
