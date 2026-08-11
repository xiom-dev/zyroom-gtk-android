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
 * L'écran des bêtes reste utile sans elle : il donne le nom, l'état et les
 * **coordonnées** de chaque bête, et ce sont les coordonnées qu'on tape en jeu
 * pour aller la chercher. La carte ne servait qu'à situer la région d'un coup
 * d'œil.
 */
const val CARTE_EMBARQUEE = false

@Composable
fun CarteBetes(betes: List<Bete>, modifier: Modifier = Modifier) {
}
