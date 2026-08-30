package net.ryzom.zyroom.ui

import androidx.compose.foundation.lazy.LazyListState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawWithContent
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Une barre de défilement sur le bord droit d'une liste.
 *
 * Compose n'en fournit pas pour les listes paresseuses — sur téléphone, on
 * défile au doigt et rien ne dit où l'on en est. Un journal de mille lignes se
 * parcourt pourtant à l'aveugle : la barre dit d'un coup d'œil s'il reste dix
 * lignes ou mille sous le pouce.
 *
 * Elle se dessine par-dessus le contenu, sans occuper de place ni intercepter
 * la moindre touche : la liste garde toute sa largeur.
 *
 * La position se déduit de la hauteur des lignes visibles. Elles n'ont pas
 * toutes la même — un nom d'objet long passe sur deux lignes —, et la moyenne
 * suffit : la barre indique où l'on est, elle ne mesure pas.
 */
fun Modifier.barreDeDefilement(
    etat: LazyListState,
    couleur: Color,
    largeur: Dp = 4.dp,
    minimumPoignee: Dp = 28.dp,
): Modifier = drawWithContent {
    drawContent()

    val info = etat.layoutInfo
    val visibles = info.visibleItemsInfo
    // Rien a montrer tant que tout tient dans l'ecran : une barre pleine
    // hauteur n'apprend rien et salit la liste.
    if (visibles.isEmpty() || info.totalItemsCount <= visibles.size) return@drawWithContent

    val hauteurMoyenne = visibles.sumOf { it.size }.toFloat() / visibles.size
    if (hauteurMoyenne <= 0f) return@drawWithContent

    val poignee = poigneeDefilement(
        hauteurVue = size.height,
        hauteurTotale = hauteurMoyenne * info.totalItemsCount,
        defile = etat.firstVisibleItemIndex * hauteurMoyenne +
            etat.firstVisibleItemScrollOffset,
        minimum = minimumPoignee.toPx(),
    )

    val largeurPx = largeur.toPx()
    drawRoundRect(
        color = couleur,
        topLeft = Offset(size.width - largeurPx, poignee.haut),
        size = Size(largeurPx, poignee.hauteur),
        cornerRadius = CornerRadius(largeurPx / 2f),
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
