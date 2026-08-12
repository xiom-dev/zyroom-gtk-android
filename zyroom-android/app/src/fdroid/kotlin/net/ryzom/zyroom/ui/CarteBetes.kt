package net.ryzom.zyroom.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import net.ryzom.zyroom.model.Bete

/**
 * Cette variante n'embarque pas la carte d'Atys.
 *
 * L'image est une donnée du jeu, republiée sous licence libre par un tiers :
 * même catégorie que les symboles de matières, et même choix — une logithèque
 * ne publie que ce dont la licence est établie de bout en bout.
 *
 * L'écran des bêtes reste utile sans elle : il dit lesquelles sont dehors, à
 * l'écurie, et où en est leur satiété. Il ne dit pas où elles sont — c'était le
 * rôle de la carte.
 */
const val CARTE_EMBARQUEE = false

@Composable
fun CarteBetes(
    betes: List<Bete>,
    joueur: Triple<String, Int, Int>? = null,
    modifier: Modifier = Modifier,
) {
}
