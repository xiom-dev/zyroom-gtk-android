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
 * rien n'empêche une logithèque de les publier. L'écran dit donc le lieu et les
 * coordonnées — « Sources Interdites · 3291 ; -10981 » —, ce qui est ce qu'on
 * tape en jeu pour poser un repère.
 *
 * C'est un gain, pas un manque : avant, cette variante ne disait rien du tout de
 * l'endroit où sortent les matières.
 */
const val GISEMENTS_EMBARQUES = false

@Composable
fun CarteDesGisements(points: List<Gisements.Point>, modifier: Modifier) {
}
