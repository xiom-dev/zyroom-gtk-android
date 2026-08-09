package net.ryzom.zyroom.ui

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import net.ryzom.zyroom.model.MINUTES_PAR_CYCLE
import net.ryzom.zyroom.model.Meteo
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * La courbe d'humidité dans le temps, avec les seuils de condition.
 *
 * Une suite de pourcentages ne se lit pas : on veut voir où l'on est, où ça
 * descend, et dans combien de temps. Les trois traits horizontaux sont les
 * seuils du jeu — 16,66 %, 50 % et 83,33 % — qui découpent les quatre
 * conditions de gisement. Sous le premier trait, c'est excellent.
 *
 * L'axe du temps est en heures réelles : un cycle vaut neuf minutes, et
 * annoncer des numéros de cycle ne parlerait à personne. Le trait vertical
 * marque l'instant présent ; tout ce qui est à sa droite est une prévision,
 * que le jeu calcule et non devine.
 */
@Composable
fun CourbeMeteo(
    cycles: List<Meteo>,
    cycleCourant: Int,
    modifier: Modifier = Modifier,
    hauteur: Int = 200,
) {
    if (cycles.size < 2) return
    val mesure = rememberTextMeasurer()
    val couleurCourbe = MaterialTheme.colorScheme.primary
    val couleurSeuil = MaterialTheme.colorScheme.error.copy(alpha = 0.55f)
    val couleurAxe = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.4f)
    val couleurTexte = MaterialTheme.colorScheme.onSurfaceVariant
    val couleurMaintenant = MaterialTheme.colorScheme.secondary
    val remplissage = couleurCourbe.copy(alpha = 0.18f)

    // Tout se dessine dans le canevas, marges comprises : Compose refuse un
    // texte posé en dehors, et le plantage n'apparaît qu'au premier rendu.
    Box(modifier.fillMaxWidth().height(hauteur.dp).padding(horizontal = 8.dp,
                                                           vertical = 6.dp)) {
        Canvas(Modifier.fillMaxWidth().height((hauteur - 12).dp)) {
            val margeGauche = 30f
            // Une étiquette de 10 sp fait une trentaine de pixels de haut : une
            // marge plus courte lui couperait le jambage du « h ».
            val margeBas = 4f + 10.sp.toPx() * 1.4f
            val largeur = size.width - margeGauche
            val haut = size.height - margeBas
            if (largeur <= 0f || haut <= 0f) return@Canvas
            fun x(index: Int) = margeGauche + largeur * index / (cycles.size - 1).toFloat()
            fun y(valeur: Double) = haut * (1f - valeur.toFloat()).coerceIn(0f, 1f)

            // Les trois seuils, en pointillé : ce sont eux qui décident de la
            // condition, la courbe seule ne dit rien.
            val pointille = PathEffect.dashPathEffect(floatArrayOf(8f, 8f))
            listOf(0.1666f to "16", 0.5f to "50", 0.8333f to "83").forEach { (v, texte) ->
                val yy = y(v.toDouble())
                drawLine(couleurSeuil, Offset(margeGauche, yy), Offset(size.width, yy),
                         strokeWidth = 1.5f, pathEffect = pointille)
                etiquette(mesure, texte, Offset(0f, (yy - 14f).coerceAtLeast(0f)),
                          couleurTexte)
            }

            // La courbe et son aire : l'aire fait lire d'un coup les creux, qui
            // sont justement les bonnes fenêtres.
            val trace = Path()
            val aire = Path()
            cycles.forEachIndexed { i, m ->
                val px = x(i)
                val py = y(m.value)
                if (i == 0) { trace.moveTo(px, py); aire.moveTo(px, haut); aire.lineTo(px, py) }
                else { trace.lineTo(px, py); aire.lineTo(px, py) }
            }
            aire.lineTo(x(cycles.size - 1), haut)
            aire.close()
            drawPath(aire, remplissage)
            drawPath(trace, couleurCourbe, style = Stroke(width = 3.5f))

            val iMaintenant = cycles.indexOfFirst { it.cycle == cycleCourant }
            if (iMaintenant >= 0) {
                drawLine(couleurMaintenant, Offset(x(iMaintenant), 0f),
                         Offset(x(iMaintenant), haut), strokeWidth = 2f)
            }
            drawLine(couleurAxe, Offset(margeGauche, haut), Offset(size.width, haut),
                     strokeWidth = 1f)

            // L'heure réelle, toutes les heures : des numéros de cycle ne
            // parleraient à personne.
            val parHeure = 60 / MINUTES_PAR_CYCLE
            val depart = LocalTime.now()
            cycles.indices.forEach { i ->
                if (iMaintenant < 0 || (i - iMaintenant) % parHeure != 0) return@forEach
                val heure = depart.plusMinutes(
                    ((i - iMaintenant) * MINUTES_PAR_CYCLE).toLong())
                val px = (x(i) - 16f).coerceIn(0f, size.width - 34f)
                etiquette(mesure, heure.format(HEURE), Offset(px, haut + 4f), couleurTexte)
            }
        }
    }
}

private val HEURE: DateTimeFormatter = DateTimeFormatter.ofPattern("HH'h'")

private fun androidx.compose.ui.graphics.drawscope.DrawScope.etiquette(
    mesure: TextMeasurer, texte: String, position: Offset, couleur: Color,
) {
    drawText(mesure, texte, position,
             style = TextStyle(color = couleur, fontSize = 10.sp))
}
