package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.gestures.detectTapGestures
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
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.input.pointer.positionChange
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
 * auteur a donné son accord écrit. Une variante qui n'embarquerait pas la
 * carte les afficherait en clair, faute de support pour les porter.
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

/** Jusqu'où le pincement peut agrandir, au-delà du cadrage d'ouverture. */
private const val ZOOM_MAX_GISEMENT = 8f

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
    // Le zoom d'ouverture, celui qui cadre sur les gisements : c'est là que le
    // double-tap ramène, et non à la carte du monde entier.
    var zoomInitial by remember { mutableFloatStateOf(1f) }

    /** Ce que le zoom laisse dépasser du cadre, de part et d'autre. */
    fun borne() {
        val debordX = (cadre.width * (zoom - 1)) / 2f
        val debordY = (cadre.height * (zoom - 1)) / 2f
        glissement = Offset(glissement.x.coerceIn(-debordX, debordX),
                            glissement.y.coerceIn(-debordY, debordY))
    }

    /**
     * Le geste se lit dans la passe initiale, comme sur la carte des bêtes.
     *
     * Deux doigts agrandissent et déplacent, toujours. **Un doigt ne déplace que
     * si l'on a agrandi au-delà du cadrage d'ouverture** : la carte s'ouvre déjà
     * agrandie sur les gisements, et si un doigt la déplaçait dès cet instant,
     * il n'y aurait plus moyen de faire défiler la boîte de dialogue — dont la
     * carte occupe la moitié, et dont le bouton « Fermer » tombe hors de vue sur
     * un écran couché.
     */
    val gestes = Modifier.pointerInput(Unit) {
        awaitEachGesture {
            awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
            do {
                val evenement = awaitPointerEvent(PointerEventPass.Initial)
                val doigts = evenement.changes.size
                if (doigts >= 2 || (doigts == 1 && zoom > zoomInitial * 1.05f)) {
                    val facteur = if (doigts >= 2) evenement.calculateZoom() else 1f
                    val deplacement = if (doigts >= 2) evenement.calculatePan()
                                      else evenement.changes[0].positionChange()
                    if (facteur != 1f || deplacement != Offset.Zero) {
                        val avant = zoom
                        zoom = (zoom * facteur).coerceIn(1f, ZOOM_MAX_GISEMENT)
                        glissement = Offset(
                            glissement.x * zoom / avant + deplacement.x,
                            glissement.y * zoom / avant + deplacement.y,
                        )
                        borne()
                        evenement.changes.forEach { it.consume() }
                    }
                }
            } while (evenement.changes.any { it.pressed })
        }
    }

    /**
     * Le double-tap agrandit **sur le point touché**, et revient au cadrage
     * d'origine quand on y est déjà.
     *
     * Le pincement demande deux doigts et une main libre ; le double-tap se fait
     * d'un pouce, en jouant. Sur le centre il ne servirait à rien : les
     * marqueurs sortiraient du cadre au premier agrandissement.
     */
    val doubleTap = Modifier.pointerInput(Unit) {
        detectTapGestures(onDoubleTap = { touche ->
            val avant = zoom
            val apres = if (zoom > zoomInitial * 1.05f) zoomInitial
                        else (zoomInitial * 2f).coerceAtMost(ZOOM_MAX_GISEMENT)
            val base = cadre.width / image.width.toFloat()
            val coinAvant = Offset(
                (cadre.width - image.width * base * avant) / 2 + glissement.x,
                (cadre.height - image.height * base * avant) / 2 + glissement.y,
            )
            val rapport = apres / avant
            val coinApres = touche - (touche - coinAvant) * rapport
            zoom = apres
            glissement = Offset(
                coinApres.x - (cadre.width - image.width * base * apres) / 2,
                coinApres.y - (cadre.height - image.height * base * apres) / 2,
            )
            borne()
        })
    }

    val couleurMarque = MaterialTheme.colorScheme.secondary
    val couleurOmbre = MaterialTheme.colorScheme.surface

    Box(modifier.fillMaxWidth()) {
        Canvas(
            Modifier.fillMaxWidth()
                .height((image.height * 1f / image.width * 340).dp)
                // La taille se relève à la mesure, jamais au dessin : y écrire
                // un état relance une recomposition à chaque image.
                .onSizeChanged { cadre = it }
                .then(gestes)
                .then(doubleTap),
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
                    zoom = (voulue / base).coerceIn(1f, ZOOM_MAX_GISEMENT)
                    zoomInitial = zoom
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
