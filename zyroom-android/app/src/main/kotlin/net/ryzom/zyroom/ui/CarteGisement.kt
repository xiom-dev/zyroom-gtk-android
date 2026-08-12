package net.ryzom.zyroom.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
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
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog

/**
 * Où sort une matière : les vues du tracker, l'une sous l'autre.
 *
 * L'écran météo dit *quoi* sort ; ceci dit *où*. Plusieurs vues quand le
 * gisement sort à plusieurs endroits — jusqu'à six pour certaines excellentes.
 * Chacune porte son marqueur et son nom, tels que le site les dessine : on ne
 * redessine rien par-dessus, ce serait doubler ce qui est déjà écrit.
 *
 * La variante F-Droid n'embarque pas ces images ; elle n'ouvre donc jamais
 * cette fenêtre, puisque rien n'y est cliquable.
 */
@Composable
fun CarteGisement(
    qualite: String,
    famille: String,
    matiere: String,
    onFermer: () -> Unit,
) {
    val cartes = cartesGisement(qualite, famille, matiere)
    if (cartes.isEmpty()) return
    Dialog(onDismissRequest = onFermer) {
        Surface(shape = RoundedCornerShape(16.dp), tonalElevation = 6.dp) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    "$matiere — $famille",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Medium,
                )
                Text(
                    entete(qualite, famille, matiere),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(bottom = 10.dp),
                )
                Column(
                    // Bornée en hauteur : six vues dépassent l'écran, et une
                    // boîte de dialogue qui déborde ne se referme plus.
                    Modifier.heightIn(max = 460.dp)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    cartes.forEach { dessin ->
                        Image(
                            painterResource(dessin),
                            contentDescription = null,
                            contentScale = ContentScale.FillWidth,
                            modifier = Modifier.fillMaxWidth()
                                .clip(RoundedCornerShape(8.dp)),
                        )
                    }
                }
                Text(
                    "Cartes : tracker d'atys.us · données de ballisticmystix.net",
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
 * « Suprême · humidité 0–16,6 %, 83,4–100 % ».
 *
 * La virgule décimale du français, et pas d'espace autour du tiret : deux
 * fourchettes doivent tenir sur une ligne de boîte de dialogue.
 */
private fun entete(qualite: String, famille: String, matiere: String): String {
    val mot = if (qualite == "supreme") "Suprême" else "Excellente"
    val fourchettes = humiditesGisement(qualite, famille, matiere)
    if (fourchettes.isEmpty()) return mot
    val taux = fourchettes.joinToString(", ") { (bas, haut) ->
        "${nombre(bas)}–${nombre(haut)} %"
    }
    return "$mot · humidité $taux"
}

/** 16.6 -> « 16,6 », 100.0 -> « 100 ». */
private fun nombre(valeur: Float): String =
    (if (valeur == valeur.toInt().toFloat()) valeur.toInt().toString()
     else valeur.toString()).replace('.', ',')
