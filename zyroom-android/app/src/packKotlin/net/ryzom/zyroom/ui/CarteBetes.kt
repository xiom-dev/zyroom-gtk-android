package net.ryzom.zyroom.ui

import android.graphics.BitmapFactory
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.gestures.awaitFirstDown
import androidx.compose.foundation.gestures.calculatePan
import androidx.compose.foundation.gestures.calculateZoom
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.input.pointer.PointerEventPass
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import net.ryzom.zyroom.R
import net.ryzom.zyroom.model.Bete
import net.ryzom.zyroom.model.CarteAtys
import kotlin.math.roundToInt

/** Cette variante embarque la carte : l'écran des bêtes peut la montrer. */
const val CARTE_EMBARQUEE = true

/**
 * Réduction appliquée à la carte au décodage.
 *
 * L'image fait quatre mille pixels de large ; décodée en entier, elle occupe
 * une trentaine de mégaoctets en mémoire pour être ensuite affichée sur un
 * écran qui en fait mille. Réduite de moitié, elle en occupe six en RGB_565 —
 * et il reste de la matière pour agrandir au pincement avant que ça ne
 * devienne flou.
 */
private const val REDUCTION = 2

/** Jusqu'où le pincement agrandit. Au-delà, on n'ajoute plus que du flou. */
private const val ZOOM_MAX = 6f

/**
 * En deçà de cette distance à l'écran, deux bêtes n'en font qu'une.
 *
 * Quarante pixels : de quoi séparer deux troupeaux laissés dans deux régions,
 * sans écrire quatre fois le même nom pour quatre mektoubs attachés ensemble.
 * Le seuil se mesure à l'écran, donc **agrandir sépare le groupe** — c'est
 * précisément à ça que sert le pincement.
 */
private const val SEUIL_GROUPE = 40f

/**
 * La carte d'Atys, et les bêtes qui y sont.
 *
 * Ce n'est pas une carte de navigation : elle sert à comprendre d'un coup d'œil
 * dans quelle région une bête a été laissée. Les coordonnées exactes sont
 * écrites sous chaque bête, dans la liste — c'est elles qu'on tape en jeu.
 *
 * Elle s'agrandit au pincement et se déplace au doigt, parce que le monde
 * entier tient dans la hauteur d'une carte de visite : deux bêtes séparées de
 * cinq cents mètres y sont au même endroit.
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

    var zoom by remember { mutableFloatStateOf(1f) }
    var glissement by remember { mutableStateOf(Offset.Zero) }
    var cadre by remember { mutableStateOf(IntSize.Zero) }

    /**
     * Le geste se lit dans la passe initiale, comme celui de l'écran météo, et
     * n'est retenu qu'à partir de deux doigts.
     *
     * Le composant standard `transformable` se serait fait voler le
     * déplacement par la liste qui défile autour : ici on consomme l'événement
     * avant elle, et un glissement à un doigt lui reste acquis — on continue
     * donc de faire défiler la liste en passant sur la carte.
     */
    val gestes = Modifier.pointerInput(Unit) {
        awaitEachGesture {
            awaitFirstDown(requireUnconsumed = false, pass = PointerEventPass.Initial)
            do {
                val evenement = awaitPointerEvent(PointerEventPass.Initial)
                if (evenement.changes.size >= 2) {
                    val facteur = evenement.calculateZoom()
                    val deplacement = evenement.calculatePan()
                    if (facteur != 1f || deplacement != Offset.Zero) {
                        val avant = zoom
                        zoom = (zoom * facteur).coerceIn(1f, ZOOM_MAX)
                        // Le déplacement se borne au débord réel, sinon la
                        // carte s'échappe de son cadre et on ne voit que du
                        // vide.
                        val debordX = (cadre.width * (zoom - 1)) / 2f
                        val debordY = (cadre.height * (zoom - 1)) / 2f
                        glissement = Offset(
                            (glissement.x * zoom / avant + deplacement.x)
                                .coerceIn(-debordX, debordX),
                            (glissement.y * zoom / avant + deplacement.y)
                                .coerceIn(-debordY, debordY),
                        )
                        evenement.changes.forEach { it.consume() }
                    }
                }
            } while (evenement.changes.any { it.pressed })
        }
    }

    val couleurMarque = MaterialTheme.colorScheme.secondary
    val couleurOmbre = MaterialTheme.colorScheme.surface
    Box(modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
        Canvas(
            Modifier.fillMaxWidth()
                .height((image.height * 1f / image.width * 340).dp)
                .then(gestes)
        ) {
            cadre = IntSize(size.width.toInt(), size.height.toInt())
            // L'échelle qui fait tenir la carte dans le cadre, multipliée par
            // l'agrandissement demandé. Le glissement est déjà en pixels
            // d'écran : il s'ajoute après.
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
                // Les bêtes se suivent : quatre mektoubs laissés ensemble
                // tombent sur le même pixel, et quatre étiquettes superposées
                // ne se lisent plus. On groupe ce qui est trop proche pour être
                // distingué **à l'écran** — agrandir les sépare donc.
                fun place(bete: Bete) = Offset(
                    coin.x + CarteAtys.x(bete.x) / REDUCTION * echelle,
                    coin.y + CarteAtys.y(bete.y) / REDUCTION * echelle,
                )
                dehors.groupBy {
                    val p = place(it)
                    Pair((p.x / SEUIL_GROUPE).toInt(), (p.y / SEUIL_GROUPE).toInt())
                }.values.forEach { groupe ->
                    val p = place(groupe[0])
                    marqueur(p.x, p.y, couleurMarque, couleurOmbre)
                    val nom = groupe[0].nom.ifEmpty { groupe[0].etiquette }
                    etiquetteBete(mesure,
                                  if (groupe.size > 1) "$nom +${groupe.size - 1}" else nom,
                                  Offset(p.x + 9.dp.toPx(), p.y - 9.dp.toPx()),
                                  couleurMarque, couleurOmbre)
                }
            }
        }
    }
}

/**
 * Le point où se tient la bête : une cible, pas un anneau.
 *
 * Trois cercles concentriques — cerne noir, disque blanc, cœur rouge — parce
 * que la carte passe du vert sombre des forêts au sable clair, au rouge du
 * désert et au violet des zones corrompues : aucune teinte unique ne s'y
 * détache partout, mais le contraste noir sur blanc, lui, tient sur tout.
 */
private fun DrawScope.marqueur(x: Float, y: Float, teinte: Color, ombre: Color) {
    // En points, et non en pixels : sur un écran qui compte trois pixels par
    // point, un rayon de huit pixels donnait un marqueur de cinq points de
    // large là où le nom en fait douze de haut. Il passait inaperçu.
    drawCircle(CERNE, radius = 6.dp.toPx(), center = Offset(x, y))
    drawCircle(Color.White, radius = 4.5f.dp.toPx(), center = Offset(x, y))
    drawCircle(POINT, radius = 2.5f.dp.toPx(), center = Offset(x, y))
}

/** Le rouge du point. Il n'existe nulle part ailleurs sur la carte à ce ton. */
private val POINT = Color(0xFFFF2D2D)

/** Le noir des cernes et des liserés, jamais tout à fait noir pour l'œil. */
private val CERNE = Color(0xFF101418)

/**
 * Le nom de la bête, en blanc, cerné de noir sur ses huit côtés.
 *
 * C'est la solution des cartes de toujours, et la seule qui tienne ici : l'or
 * du thème se perdait sur le sable, et une couleur vive se perd ailleurs. Le
 * blanc cerné de noir se lit sur la forêt, sur le désert, sur le vide.
 *
 * Deux décalages en diagonale ne suffisaient pas — le liseré manquait au-dessus
 * et sur les côtés, là où le fond est clair. Il en faut huit.
 *
 * La taille ne suit pas l'agrandissement : un nom grand comme une région se
 * lirait moins bien, pas mieux.
 */
private fun DrawScope.etiquetteBete(
    mesure: TextMeasurer, texte: String, position: Offset, teinte: Color, ombre: Color,
) {
    val style = TextStyle(fontSize = 12.sp)
    val cerne = style.copy(color = CERNE)
    for (dx in -1..1) for (dy in -1..1) {
        if (dx != 0 || dy != 0) {
            drawText(mesure, texte,
                     position + Offset(dx * 0.7f.dp.toPx(), dy * 0.7f.dp.toPx()),
                     style = cerne)
        }
    }
    drawText(mesure, texte, position, style = style.copy(color = Color.White))
}
