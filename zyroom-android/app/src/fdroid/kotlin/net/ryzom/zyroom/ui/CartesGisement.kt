package net.ryzom.zyroom.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import net.ryzom.zyroom.model.Gisements

/**
 * Cette variante n'embarque pas la carte d'Atys, donc rien à dessiner dessus.
 *
 * **Mais elle a les positions.** Elles viennent du relevé de
 * ballisticmystix.net, dont l'auteur a donné son accord écrit pour qu'on s'en
 * serve et qu'on le redistribue : ce sont des faits, pas des images du jeu, et
 * rien n'empêche une logithèque de les publier. L'écran nomme donc les lieux —
 * « Sources Interdites », « Porte des Vents ». Sans les coordonnées : le jeu ne
 * permet pas d'en saisir, elles n'apprendraient rien.
 *
 * C'est un gain, pas un manque : avant, cette variante ne disait rien du tout de
 * l'endroit où sortent les matières.
 */
const val GISEMENTS_EMBARQUES = false

@Composable
fun CarteDesGisements(points: List<Gisements.Point>, modifier: Modifier) {
}
