package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp
import net.ryzom.zyroom.model.Item

/**
 * Les gouttes de spécialité, posées par-dessus l'icône d'un équipement.
 *
 * Une armure, une arme ou un bijou craftés portent des bonus qui dépendent des
 * matières employées : vie, sève, endurance, concentration. Le jeu les résume
 * par une goutte de couleur ; l'icône que renvoie `item_icon.php` ne les
 * connaît pas — l'API n'a que le nom de fiche, la couleur et la qualité,
 * jamais l'exemplaire. On les dessine donc par-dessus.
 *
 * Portage de `zyroom/specialites.py` de la variante GTK : mêmes couleurs, même
 * ordre, même coin. Les deux applications montrent le même coffre ; elles
 * doivent le montrer pareil.
 */

/** (nom du bonus, sa valeur sur l'item, sa couleur), dans l'ordre des jauges. */
private val SPECIALITES: List<Triple<String, (Item) -> Int, Color>> = listOf(
    Triple("Vie", { it: Item -> it.hpBuff }, Color(0xFFE2696A)),
    Triple("Sève", { it: Item -> it.sapBuff }, Color(0xFF4CAF50)),
    Triple("Endurance", { it: Item -> it.staBuff }, Color(0xFFA97FD0)),
    Triple("Concentration", { it: Item -> it.focusBuff }, Color(0xFF4A90D9)),
)

/** La goutte, en dp. Un quart d'une case de grille, comme sur le bureau. */
private val LARGEUR = 9.dp
private val HAUTEUR = 12.dp

/** Les bonus que porte l'item : `(libellé, valeur, couleur)`. */
fun bonusDe(item: Item): List<Triple<String, Int, Color>> =
    SPECIALITES.mapNotNull { (libelle, valeur, couleur) ->
        val nombre = valeur(item)
        if (nombre > 0) Triple(libelle, nombre, couleur) else null
    }

/** « Vie +125, Sève +20 », pour la fiche d'un objet. */
fun resumeBonus(item: Item): String =
    bonusDe(item).joinToString(", ") { (libelle, valeur, _) -> "$libelle +$valeur" }

/**
 * La pile de gouttes à poser sur l'icône, du haut vers le bas.
 *
 * Rien ne se dessine si l'objet n'a aucun bonus — c'est le cas de presque tout
 * un coffre de matières.
 *
 * **En haut à gauche** : l'API écrit la qualité en bas à droite, empile les
 * étoiles de classe en haut à droite, et la quantité occupe le bas. C'est le
 * seul coin libre, et c'est celui qu'occupe déjà la version GTK.
 */
@Composable
fun PileDeGouttes(item: Item, modifier: Modifier = Modifier) {
    val couleurs = bonusDe(item).map { (_, _, couleur) -> couleur }
    if (couleurs.isEmpty()) return

    Canvas(modifier = modifier.size(LARGEUR, HAUTEUR * couleurs.size)) {
        val largeur = size.width
        val hauteur = size.height / couleurs.size
        // De bas en haut : quand deux gouttes se touchent, c'est la pointe qui
        // passe sous celle du dessus, jamais le ventre -- le ventre porte la
        // couleur, donc le sens.
        for (rang in couleurs.indices.reversed()) {
            val haut = rang * hauteur
            val rayon = minOf(largeur, hauteur) / 2f - 1f
            val centre = Offset(largeur / 2f, haut + hauteur - rayon - 1f)

            val chemin = Path().apply {
                // Le ventre : les deux tiers bas du cercle, de -30 a 210
                // degres, puis les flancs remontent vers la pointe.
                arcTo(
                    rect = Rect(
                        Offset(centre.x - rayon, centre.y - rayon),
                        Size(rayon * 2f, rayon * 2f),
                    ),
                    startAngleDegrees = -30f,
                    sweepAngleDegrees = 240f,
                    forceMoveTo = true,
                )
                lineTo(centre.x, haut + 1f)
                close()
            }
            drawPath(chemin, couleurs[rang])
            // Un cerne sombre : les icones de Ryzom sont claires et chargees,
            // une pastille sans contour s'y dissout.
            drawPath(chemin, Color.Black.copy(alpha = 0.75f), style = Stroke(width = 1f))
        }
    }
}
