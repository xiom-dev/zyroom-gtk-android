package net.ryzom.zyroom.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import net.ryzom.zyroom.R
import net.ryzom.zyroom.model.Bete
import net.ryzom.zyroom.model.CarteAtys

/** Cette variante embarque la carte : l'écran des bêtes peut la montrer. */
const val CARTE_EMBARQUEE = true

/**
 * Réduction appliquée à la carte au décodage.
 *
 * L'image fait quatre mille pixels de large ; décodée en entier, elle occupe
 * une trentaine de mégaoctets en mémoire pour être ensuite affichée sur un
 * écran qui en fait mille. On la décode donc au quart, et l'échelle du repère
 * suit — c'est tout l'intérêt d'avoir la correspondance en dur plutôt qu'en
 * pixels d'image.
 */
private const val REDUCTION = 4

/**
 * En deçà de cette distance à l'écran, deux bêtes n'en font qu'une.
 *
 * Quarante pixels : de quoi séparer deux troupeaux laissés dans deux régions,
 * sans écrire quatre fois le même nom pour quatre mektoubs attachés ensemble.
 */
private const val SEUIL_GROUPE = 40f

/**
 * La carte d'Atys, et les bêtes qui y sont.
 *
 * Ce n'est pas une carte de navigation : elle sert à comprendre d'un coup d'œil
 * dans quelle région une bête a été laissée. Les coordonnées exactes sont
 * écrites sous chaque bête, dans la liste — c'est elles qu'on tape en jeu.
 *
 * Seules les bêtes dehors y figurent : une bête à l'écurie est là où on l'a
 * rangée, et sa position ne veut rien dire.
 */
@Composable
fun CarteBetes(betes: List<Bete>, modifier: Modifier = Modifier) {
    val dehors = betes.filter { it.dehors && CarteAtys.contient(it.x, it.y) }
    if (dehors.isEmpty()) return
    val contexte = LocalContext.current
    val mesure = rememberTextMeasurer()
    val image = remember {
        val options = BitmapFactory.Options().apply {
            inSampleSize = REDUCTION
            inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
        }
        BitmapFactory.decodeResource(contexte.resources, R.drawable.carte_atys, options)
            ?.asImageBitmap()
    } ?: return

    val couleurMarque = MaterialTheme.colorScheme.secondary
    val couleurOmbre = MaterialTheme.colorScheme.surface
    Box(modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
        Canvas(Modifier.fillMaxWidth()
                   .height((image.height * 1f / image.width * 340).dp)) {
            val echelle = size.width / image.width
            drawImage(image, dstSize = androidx.compose.ui.unit.IntSize(
                size.width.toInt(), (image.height * echelle).toInt()))
            // Les bêtes se suivent : quatre mektoubs laissés ensemble tombent
            // sur le même pixel, et quatre étiquettes superposées ne se lisent
            // plus. On groupe ce qui est trop proche pour être distingué, et on
            // n'écrit qu'un nom, suivi du nombre.
            dehors.groupBy {
                Pair((CarteAtys.x(it.x) / REDUCTION * echelle / SEUIL_GROUPE).toInt(),
                     (CarteAtys.y(it.y) / REDUCTION * echelle / SEUIL_GROUPE).toInt())
            }.values.forEach { groupe ->
                val x = CarteAtys.x(groupe[0].x) / REDUCTION * echelle
                val y = CarteAtys.y(groupe[0].y) / REDUCTION * echelle
                marqueur(x, y, couleurMarque, couleurOmbre)
                val nom = groupe[0].nom.ifEmpty { groupe[0].etiquette }
                etiquetteBete(mesure,
                              if (groupe.size > 1) "$nom +${groupe.size - 1}" else nom,
                              Offset(x + 9f, y - 12f), couleurMarque, couleurOmbre)
            }
        }
    }
}

/** Un anneau clair cerné de sombre : lisible sur la forêt comme sur le désert. */
private fun DrawScope.marqueur(x: Float, y: Float, teinte: Color, ombre: Color) {
    drawCircle(ombre, radius = 8f, center = Offset(x, y))
    drawCircle(teinte, radius = 5f, center = Offset(x, y))
    drawCircle(ombre, radius = 2f, center = Offset(x, y))
}

/**
 * Le nom de la bête, doublé d'un liseré sombre.
 *
 * Sans lui, un nom clair posé sur les zones sableuses de la carte disparaît.
 */
private fun DrawScope.etiquetteBete(
    mesure: TextMeasurer, texte: String, position: Offset, teinte: Color, ombre: Color,
) {
    val style = TextStyle(fontSize = 11.sp)
    listOf(-1f, 1f).forEach { d ->
        drawText(mesure, texte, position + Offset(d, d), style = style.copy(color = ombre))
    }
    drawText(mesure, texte, position, style = style.copy(color = teinte))
}
