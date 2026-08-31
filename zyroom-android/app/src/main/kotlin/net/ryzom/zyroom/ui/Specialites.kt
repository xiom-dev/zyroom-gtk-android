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
import net.ryzom.zyroom.model.Jauge

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

/**
 * La couleur de chaque jauge, dans l'ordre des jauges.
 *
 * L'ordre et les libellés viennent de `Jauge`, côté modèle : le filtre range
 * ses cases dessus, et deux listes parallèles finiraient par diverger. Ne
 * restent ici que les couleurs, qui sont affaire de dessin.
 */
val COULEUR_JAUGE: Map<Jauge, Color> = mapOf(
    Jauge.VIE to Color(0xFFE2696A),
    Jauge.SEVE to Color(0xFF4CAF50),
    Jauge.ENDURANCE to Color(0xFFA97FD0),
    Jauge.CONCENTRATION to Color(0xFF4A90D9),
)

/** La goutte, en dp. Un quart d'une case de grille, comme sur le bureau. */
private val LARGEUR = 9.dp
private val HAUTEUR = 12.dp

/** Les bonus que porte l'item : `(libellé, valeur, couleur)`. */
fun bonusDe(item: Item): List<Triple<String, Int, Color>> =
    Jauge.entries.mapNotNull { jauge ->
        val nombre = jauge.valeur(item)
        if (nombre > 0) Triple(jauge.label, nombre, COULEUR_JAUGE.getValue(jauge)) else null
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
            val chemin = cheminDeGoutte(largeur, hauteur, haut = rang * hauteur)
            drawPath(chemin, couleurs[rang])
            // Un cerne sombre : les icones de Ryzom sont claires et chargees,
            // une pastille sans contour s'y dissout.
            drawPath(chemin, Color.Black.copy(alpha = 0.75f), style = Stroke(width = 1f))
        }
    }
}

/**
 * La forme d'une goutte : pointe en haut, ventre rond en bas.
 *
 * À part, parce qu'elle sert deux fois — sur l'icône, et dans le panneau des
 * filtres, où chaque case porte la goutte de sa jauge. Deux dessins qui
 * dériveraient l'un de l'autre casseraient le lien que la couleur établit
 * entre la case cochée et l'objet marqué.
 */
fun cheminDeGoutte(largeur: Float, hauteur: Float, haut: Float = 0f): Path {
    val rayon = minOf(largeur, hauteur) / 2f - 1f
    val centre = Offset(largeur / 2f, haut + hauteur - rayon - 1f)
    return Path().apply {
        // Le ventre : les deux tiers bas du cercle, de -30 a 210 degres, puis
        // les flancs remontent vers la pointe.
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
}
