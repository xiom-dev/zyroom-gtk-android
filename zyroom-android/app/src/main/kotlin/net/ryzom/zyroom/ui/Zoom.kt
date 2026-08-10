package net.ryzom.zyroom.ui

import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density

/** Les bornes du zoom : en deçà on ne lit plus, au-delà rien ne tient à l'écran. */
private const val ZOOM_MIN = 0.6f
private const val ZOOM_MAX = 2.0f

/**
 * Le zoom à deux doigts, autour de l'écran météo.
 *
 * Pincer change la densité d'affichage, donc **tout** rétrécit ensemble —
 * textes, courbe, colonnes, marges — au lieu de rapetisser une image déjà
 * composée : le texte reste net à n'importe quel facteur, et les listes
 * continuent de se replier comme il faut.
 *
 * Il n'enveloppe que la météo, et non toute l'application : c'est le seul écran
 * dont le contenu ne s'adapte pas de lui-même — on veut tantôt lire une matière
 * précise, tantôt voir toute la saison d'un coup. Ailleurs le geste ne servait à
 * rien et pouvait surprendre : les inventaires ont leurs boutons « − » et « + »,
 * l'arbre des compétences se replie.
 *
 * Le geste se lit dans la passe initiale, avant les listes qui défilent, et
 * n'est retenu qu'à partir de deux doigts : un glissement d'un doigt reste un
 * défilement, et rien ne se met à zoomer quand on parcourt le tableau.
 */
@Composable
fun ZoomPincee(content: @Composable () -> Unit) {
    var zoom by rememberSaveable { mutableFloatStateOf(1f) }
    val densite = LocalDensity.current
    Box(
        Modifier.fillMaxSize().pointerInput(Unit) {
            awaitEachGesture {
                awaitFirstDown(requireUnconsumed = false,
                               pass = PointerEventPass.Initial)
                do {
                    val evenement = awaitPointerEvent(PointerEventPass.Initial)
                    if (evenement.changes.size >= 2) {
                        val facteur = evenement.calculateZoom()
                        if (facteur != 1f) {
                            zoom = (zoom * facteur).coerceIn(ZOOM_MIN, ZOOM_MAX)
                            evenement.changes.forEach { it.consume() }
                        }
                    }
                } while (evenement.changes.any { it.pressed })
            }
        },
    ) {
        CompositionLocalProvider(
            LocalDensity provides Density(densite.density * zoom, densite.fontScale),
            content = content,
        )
    }
}
