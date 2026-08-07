package net.ryzom.zyroom.data

import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.setValue

/**
 * Les réglages qu'on garde d'une fois sur l'autre.
 *
 * Un état, pour que l'écran suive : changer la taille des icônes doit se voir
 * aussitôt, et se retrouver au prochain lancement.
 */
class Preferences(context: Context) {

    private val store = context.getSharedPreferences("zyroom", Context.MODE_PRIVATE)

    /** Côté d'une case d'item, en points d'écran. */
    var cellSize: Int by mutableIntStateOf(
        store.getInt(CELL_SIZE, DEFAULT_CELL).coerceIn(MIN_CELL, MAX_CELL))
        private set

    /** Agrandit ou réduit d'un cran, sans sortir des bornes. */
    fun zoom(step: Int) {
        val taille = (cellSize + step).coerceIn(MIN_CELL, MAX_CELL)
        if (taille != cellSize) {
            cellSize = taille
            store.edit().putInt(CELL_SIZE, taille).apply()
        }
    }

    val canZoomIn: Boolean get() = cellSize < MAX_CELL
    val canZoomOut: Boolean get() = cellSize > MIN_CELL

    companion object {
        private const val CELL_SIZE = "cell_size"

        /** Le pas d'un cran de zoom, et les bornes. */
        const val STEP = 16
        const val MIN_CELL = 48
        const val MAX_CELL = 160
        const val DEFAULT_CELL = 72
    }
}
