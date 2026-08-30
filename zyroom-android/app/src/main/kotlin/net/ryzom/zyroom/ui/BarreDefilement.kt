package net.ryzom.zyroom.ui

import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

/**
 * Une barre de défilement saisissable, sur le bord droit d'une liste.
 *
 * Compose n'en fournit pas pour les listes paresseuses — sur téléphone, on
 * défile au doigt et rien ne dit où l'on en est. Un journal de mille lignes se
 * parcourt pourtant à l'aveugle : la barre dit d'un coup d'œil s'il reste dix
 * lignes ou mille sous le pouce, **et permet de sauter au milieu** au lieu de
 * balayer trente fois.
 *
 * Elle se pose par-dessus la liste, dans une bande de vingt-huit points de
 * large : moins, on ne l'attrape pas au pouce. La poignée s'épaissit tant
 * qu'on la tient, pour qu'on sache qu'on l'a bien saisie.
 *
 * La position se déduit de la hauteur des lignes visibles. Elles n'ont pas
 * toutes la même — un nom d'objet long passe sur deux lignes —, et la moyenne
 * suffit : la barre indique où l'on est, elle ne mesure pas.
 */
@Composable
fun BarreDefilement(
    etat: LazyListState,
    couleur: Color,
    modifier: Modifier = Modifier,
    largeur: Dp = 4.dp,
    largeurTenue: Dp = 8.dp,
    prise: Dp = 28.dp,
    minimumPoignee: Dp = 28.dp,
) {
    val portee = rememberCoroutineScope()
    var tenue by remember { mutableStateOf(false) }

    Box(
        modifier
            .fillMaxHeight()
            .width(prise)
            .pointerInput(etat) {
                detectDragGestures(
                    onDragStart = { tenue = true },
                    onDragEnd = { tenue = false },
                    onDragCancel = { tenue = false },
                ) { evenement, glissement ->
                    evenement.consume()
                    val mesure = mesurer(etat, size.height.toFloat()) ?: return@detectDragGestures

                    val poignee = poigneeDefilement(
                        mesure.vue, mesure.totale, mesure.defile, minimumPoignee.toPx(),
                    )
                    // Le doigt deplace la poignee ; le contenu suit dans le
                    // rapport de la glissiere a la course -- un point de
                    // poignee vaut dix lignes sur un long journal.
                    val glissiere = (mesure.vue - poignee.hauteur).coerceAtLeast(1f)
                    val course = (mesure.totale - mesure.vue).coerceAtLeast(1f)
                    val cible = (mesure.defile + glissement.y * course / glissiere)
                        .coerceIn(0f, course)

                    val rang = (cible / mesure.moyenne).toInt()
                        .coerceIn(0, (etat.layoutInfo.totalItemsCount - 1).coerceAtLeast(0))
                    val reste = (cible - rang * mesure.moyenne).toInt().coerceAtLeast(0)
                    portee.launch { etat.scrollToItem(rang, reste) }
                }
            }
            .drawWithContent {
                drawContent()
                val mesure = mesurer(etat, size.height) ?: return@drawWithContent
                val poignee = poigneeDefilement(
                    mesure.vue, mesure.totale, mesure.defile, minimumPoignee.toPx(),
                )
                val epaisseur = (if (tenue) largeurTenue else largeur).toPx()
                drawRoundRect(
                    color = couleur,
                    topLeft = Offset(size.width - epaisseur, poignee.haut),
                    size = Size(epaisseur, poignee.hauteur),
                    cornerRadius = CornerRadius(epaisseur / 2f),
                )
            },
    )
}

/** Ce qu'il faut savoir de la liste pour placer la poignée. */
private class Mesure(
    val vue: Float,
    val totale: Float,
    val defile: Float,
    val moyenne: Float,
)

/**
 * Mesure la liste, ou `null` quand il n'y a rien à montrer.
 *
 * Rien à montrer, c'est une liste vide ou qui tient tout entière à l'écran :
 * une barre pleine hauteur n'apprend rien et salit la vue.
 */
private fun mesurer(etat: LazyListState, hauteurVue: Float): Mesure? {
    val info = etat.layoutInfo
    val visibles = info.visibleItemsInfo
    if (visibles.isEmpty() || info.totalItemsCount <= visibles.size) return null
    val moyenne = visibles.sumOf { it.size }.toFloat() / visibles.size
    if (moyenne <= 0f) return null
    return Mesure(
        vue = hauteurVue,
        totale = moyenne * info.totalItemsCount,
        defile = etat.firstVisibleItemIndex * moyenne + etat.firstVisibleItemScrollOffset,
        moyenne = moyenne,
    )
}


/** Où se pose la poignée, et quelle hauteur elle prend. */
data class Poignee(val haut: Float, val hauteur: Float)

/**
 * La géométrie de la poignée, en pixels — la seule part où l'on se trompe.
 *
 * Sa hauteur dit quelle fraction du journal tient à l'écran, sa position où
 * l'on en est. Un minimum la garde saisissable : sur mille lignes, la
 * proportion exacte donnerait un trait d'un pixel qu'on ne verrait pas.
 */
fun poigneeDefilement(
    hauteurVue: Float,
    hauteurTotale: Float,
    defile: Float,
    minimum: Float,
): Poignee {
    val hauteur = (hauteurVue * hauteurVue / hauteurTotale)
        .coerceAtLeast(minimum)
        .coerceAtMost(hauteurVue)
    val glissiere = hauteurVue - hauteur
    // La course est ce qui reste a parcourir sous la vue, jamais zero : une
    // liste qui tient tout juste a l'ecran diviserait par rien.
    val course = (hauteurTotale - hauteurVue).coerceAtLeast(1f)
    return Poignee((defile / course * glissiere).coerceIn(0f, glissiere), hauteur)
}
