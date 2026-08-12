package net.ryzom.zyroom.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import net.ryzom.zyroom.model.Gisements

/**
 * Où sort une matière : nos propres marqueurs sur la carte d'Atys, et les
 * coordonnées en clair.
 *
 * L'écran météo dit *quoi* sort ; ceci dit *où*. On embarquait les vues rendues
 * par le tracker d'atys.us — trois mégaoctets d'images figées. Ballistic Mystix
 * a donné les coordonnées : sept kilooctets, notre carte, un zoom libre, et le
 * nom du lieu écrit à côté de chaque point.
 *
 * Les coordonnées sont écrites même quand la carte les porte : ce sont elles
 * qu'on tape en jeu pour poser un repère, et un point sur une carte ne les donne
 * pas au mètre près. Dans la variante F-Droid, qui n'embarque pas la carte, elles
 * sont tout ce qu'il y a — et c'est déjà plus que rien, ce qu'elle avait avant.
 */
@Composable
fun CarteGisement(
    qualite: String,
    famille: String,
    matiere: String,
    onFermer: () -> Unit,
) {
    val points = Gisements.points(qualite, famille, matiere)
    if (points.isEmpty()) return
    Dialog(onDismissRequest = onFermer) {
        Surface(shape = RoundedCornerShape(16.dp), tonalElevation = 6.dp) {
            // Tout défile, pas seulement la carte : un écran couché ne fait que
            // quatre cents points de haut, et avec le défilement à l'intérieur
            // seulement, le bouton « Fermer » tombait hors de vue.
            Column(
                Modifier.padding(16.dp)
                    .verticalScroll(rememberScrollState()),
            ) {
                Text(
                    "$matiere — $famille",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium,
                )
                Text(
                    entete(qualite, famille, matiere, points.size),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 10.dp),
                )
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    CarteDesGisements(points, Modifier)
                    // Pas de coordonnées : la carte les porte, et elles
                    // encombraient l'écran d'un téléphone. Les noms de lieux ne
                    // restent que dans la variante qui n'a pas de carte — sans
                    // eux, elle ne dirait plus rien du tout de l'endroit.
                    if (!GISEMENTS_EMBARQUES) {
                        points.map { it.lieu }.distinct().forEach { lieu ->
                            Text(lieu, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                Text(
                    "Positions : relevé de ballisticmystix.net, avec l'accord " +
                        "de son auteur",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 10.dp),
                )
                TextButton(onFermer, Modifier.align(Alignment.End)) {
                    Text("Fermer")
                }
            }
        }
    }
}

/**
 * « Suprême · humidité 0–16,6 % · 4 gisements ».
 *
 * La virgule décimale du français, et pas d'espace autour du tiret : deux
 * fourchettes doivent tenir sur une ligne de boîte de dialogue.
 */
private fun entete(qualite: String, famille: String, matiere: String,
                   combien: Int): String {
    val mot = if (qualite == "supreme") "Suprême" else "Excellente"
    val fourchettes = Gisements.humidites(qualite, famille, matiere)
    val taux = fourchettes.joinToString(", ") { (bas, haut) ->
        "${nombre(bas)}–${nombre(haut)} %"
    }
    val combien_ = if (combien > 1) "$combien gisements" else "1 gisement"
    return if (taux.isEmpty()) "$mot · $combien_"
           else "$mot · humidité $taux · $combien_"
}

/** 16.6 -> « 16,6 », 100.0 -> « 100 ». */
private fun nombre(valeur: Float): String =
    (if (valeur == valeur.toInt().toFloat()) valeur.toInt().toString()
     else valeur.toString()).replace('.', ',')
