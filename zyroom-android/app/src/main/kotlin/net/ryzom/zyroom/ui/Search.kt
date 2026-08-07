package net.ryzom.zyroom.ui

import java.text.Normalizer

/**
 * Recherche tolérante, portée du `_norm` de la version GTK : minuscules et sans
 * accents, pour que « legerete » trouve « Légèreté ».
 */
fun normalise(text: String): String =
    Normalizer.normalize(text, Normalizer.Form.NFKD)
        .filter { !it.isMark() }
        .lowercase()

private fun Char.isMark(): Boolean = when (Character.getType(this).toByte()) {
    Character.NON_SPACING_MARK, Character.COMBINING_SPACING_MARK,
    Character.ENCLOSING_MARK -> true
    else -> false
}
