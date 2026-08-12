package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import android.graphics.BitmapFactory
import androidx.compose.ui.graphics.asImageBitmap
import net.ryzom.zyroom.R
import net.ryzom.zyroom.model.CarteAtys
import net.ryzom.zyroom.model.Gisements
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * La carte d'Atys est embarquée dans cette variante, donc les gisements s'y
 * dessinent.
 *
 * Les positions, elles, sont dans `src/main` : ce sont des faits, et leur
 * auteur a donné son accord écrit. La variante F-Droid les affiche en clair,
 * faute de carte pour les porter.
 */
const val GISEMENTS_EMBARQUES = true

/**
 * Part du cadre que les gisements doivent occuper au premier affichage.
 *
 * Les quatre zones des Primes tiennent dans un dixième de la carte du monde :
 * sans cadrage, on voyait quatre points collés au milieu d'Atys et leurs noms se
 * chevauchaient. On garde de la marge autour, pour situer la zone dans son
 * continent plutôt que de la montrer hors contexte.
 */
private const val CADRAGE = 0.55f

/**
 * Où sortent les gisements d'une matière, sur la carte d'Atys.
 *
 * On embarquait les vues rendues par le tracker d'atys.us — trois mégaoctets
 * d'images figées, une par gisement. Ballistic Mystix a donné les coordonnées :
 * sept kilooctets, notre propre carte, et un zoom libre au lieu d'une image dont
 * on ne pouvait rien approcher.
 *
 * La vue s'ouvre cadrée sur les gisements, et le nom du lieu est écrit à côté de
 * chaque point — un point seul ne dit pas où aller.
 */
@Composable
fun CarteDesGisements(points: List<Gisements.Point>, modifier: Modifier) {
    if (points.isEmpty()) return
    val contexte = LocalContext.current
    val mesure = rememberTextMeasurer()
    val image = remember {
        val options = BitmapFactory.Options().apply {
            inSampleSize = 2
            inPreferredConfig = android.graphics.Bitmap.Config.RGB_565
        }
        BitmapFactory.decodeResource(contexte.resources, R.drawable.carte_atys, options)
            ?.asImageBitmap()
    } ?: return

    var cadre by remember { mutableStateOf(IntSize.Zero) }
    var zoom by remember { mutableFloatStateOf(1f) }
    var glissement by remember { mutableStateOf(Offset.Zero) }
    var cadré by remember { mutableStateOf(false) }

    val couleurMarque = MaterialTheme.colorScheme.secondary
    val couleurOmbre = MaterialTheme.colorScheme.surface

    Box(modifier.fillMaxWidth()) {
        Canvas(
            Modifier.fillMaxWidth()
                .height((image.height * 1f / image.width * 340).dp)
                // La taille se relève à la mesure, jamais au dessin : y écrire
                // un état relance une recomposition à chaque image.
                .onSizeChanged { cadre = it },
        ) {
            // Le cadrage a besoin de la taille du cadre : il ne peut donc se
            // calculer qu'ici, et une seule fois.
            if (!cadré && size.width > 1f) {
                val places = points.mapNotNull { CarteAtys.pixel(it.x, it.y) }
                if (places.isNotEmpty()) {
                    val xs = places.map { it.first }
                    val ys = places.map { it.second }
                    val cx = (xs.min() + xs.max()) / 2f / 2f
                    val cy = (ys.min() + ys.max()) / 2f / 2f
                    // Un seul gisement n'a pas d'étendue : on lui en donne une,
                    // sinon le zoom partirait au maximum sur un point.
                    val large = max(xs.max() - xs.min(), 300f) / 2f
                    val haute = max(ys.max() - ys.min(), 260f) / 2f
                    val base = size.width / image.width
                    val voulue = minOf(CADRAGE * size.width / large,
                                       CADRAGE * size.height / haute)
                    zoom = (voulue / base).coerceIn(1f, 6f)
                    val echelle = base * zoom
                    glissement = Offset(echelle * (image.width / 2f - cx),
                                        echelle * (image.height / 2f - cy))
                }
                cadré = true
            }
            val echelle = size.width / image.width * zoom
            val coin = Offset(
                (size.width - image.width * echelle) / 2 + glissement.x,
                (size.height - image.height * echelle) / 2 + glissement.y,
            )
            clipRect {
                drawImage(
                    image,
                    dstOffset = IntOffset(coin.x.roundToInt(), coin.y.roundToInt()),
                    dstSize = IntSize((image.width * echelle).roundToInt(),
                                      (image.height * echelle).roundToInt()),
                )
                points.forEach { point ->
                    val place = CarteAtys.pixel(point.x, point.y) ?: return@forEach
                    val px = coin.x + place.first / 2f * echelle
                    val py = coin.y + place.second / 2f * echelle
                    // Ce qui sort du cadre ne se dessine pas. `drawText` ne se
                    // contente pas d'être invisible hors du canevas : il lève
                    // « maxHeight must be >= minHeight » et fait tomber
                    // l'application.
                    if (px !in 0f..size.width || py !in 0f..size.height) {
                        return@forEach
                    }
                    marqueurGisement(px, py)
                    etiquetteBete(mesure, point.lieu,
                                  Offset(px + 9.dp.toPx(), py - 9.dp.toPx()),
                                  couleurMarque, couleurOmbre)
                }
            }
        }
    }
}
