package net.ryzom.zyroom.ui

import androidx.annotation.DrawableRes
import net.ryzom.zyroom.R
import net.ryzom.zyroom.model.SYMBOLES

/**
 * Les symboles des familles de matières sont embarqués dans cette variante.
 *
 * Ce sont des images du jeu, reprises de Ryzom Armory : on les distribue dans
 * les variantes qu'on publie soi-même, pas dans celle d'une logithèque qui
 * n'accepte que ce dont la licence est établie.
 */
const val SYMBOLES_EMBARQUES = true

/**
 * Le dessin du symbole d'une famille, ou rien si elle n'en a pas.
 *
 * La correspondance est nommée ici, une ressource à la fois, plutôt que résolue
 * par `getIdentifier` : une ressource qu'aucun code ne nomme est retirée de
 * l'APK au rétrécissement, et le symbole aurait disparu de la version publiée
 * sans jamais manquer à l'essai. Une famille que Ryzom ajouterait n'aurait pas
 * de symbole ici — elle s'affichera sans, plutôt que de faire tomber l'écran.
 */
@DrawableRes
internal fun symboleDe(groupe: String): Int? = when (SYMBOLES[groupe]) {
    "mp_amber" -> R.drawable.mp_amber
    "mp_bark" -> R.drawable.mp_bark
    "mp_fiber" -> R.drawable.mp_fiber
    "mp_oil" -> R.drawable.mp_oil
    "mp_resin" -> R.drawable.mp_resin
    "mp_sap" -> R.drawable.mp_sap
    "mp_seed" -> R.drawable.mp_seed
    "mp_shell" -> R.drawable.mp_shell
    "mp_wood" -> R.drawable.mp_wood
    "mp_wood_node" -> R.drawable.mp_wood_node
    else -> null
}
