package net.ryzom.zyroom.ui

import androidx.annotation.DrawableRes

/**
 * Cette variante n'embarque aucun symbole de matière.
 *
 * Les symboles des familles sont des images du jeu, reprises de Ryzom Armory :
 * leur licence n'est pas établie, et F-Droid ne publie que ce dont elle l'est.
 * Les images ne sont pas dans `src/main` mais dans `src/packRes`, que seules
 * les variantes qu'on distribue soi-même déclarent — elles ne sont donc ni dans
 * cet APK, ni compilables ici, d'où cette version qui ne rend rien.
 *
 * Le tableau des matières s'affiche sans eux : les familles y sont nommées, et
 * c'est le nom qui porte l'information.
 */
const val SYMBOLES_EMBARQUES = false

@DrawableRes
internal fun symboleDe(groupe: String): Int? = null
