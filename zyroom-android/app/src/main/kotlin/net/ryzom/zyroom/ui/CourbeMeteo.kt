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
import androidx.compose.ui.geometry.Size
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
import net.ryzom.zyroom.model.HEURES_PAR_CYCLE
import net.ryzom.zyroom.model.MINUTES_PAR_CYCLE
import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.estLaNuit
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * L'humidité dans le temps, en marches d'escalier.
 *
 * **Le jeu ne fait pas varier la météo en continu.** Une valeur vaut pour tout
 * un cycle — trois heures d'Atys, neuf minutes réelles — puis saute à la
 * suivante. Relier les points par des segments obliques dessinait des crêtes
 * qui n'existent pas et déplaçait les moments intéressants : la fenêtre
 * excellente n'est pas un sommet qu'on rate, c'est un palier qui dure.
 *
 * C'est ce que trace le calendrier d'Atys de Ballistic Mystix, en répétant la
 * valeur sur les trois heures du cycle ; on fait pareil, en marches.
 *
 * Les trois traits horizontaux sont les seuils du jeu — 16,66 %, 50 % et
 * 83,33 % — qui découpent les quatre conditions de gisement : sous le premier,
 * c'est excellent. Les bandes sombres sont les nuits d'Atys, que le jeu compte
 * de 22 h à 3 h : ce sont elles qui décident des matières excellentes de nuit.
 * L'axe du temps est en heures réelles — annoncer des numéros de cycle ne
 * parlerait à personne — et le trait vertical marque l'instant présent, tout ce
 * qui est à sa droite étant une prévision que le jeu calcule et non devine.
 */
@Composable
fun CourbeMeteo(
    releve: MeteoAtys,
    cycles: List<Meteo>,
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
    val couleurNuit = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.07f)
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

            // L'axe se compte en cycles, bornes comprises : le dernier palier
            // occupe une case comme les autres, sinon la courbe s'arrêterait
            // avant le bord.
            val cases = cycles.size.toFloat()
            fun x(position: Float) = margeGauche + largeur * position / cases
            fun y(valeur: Double) = haut * (1f - valeur.toFloat()).coerceIn(0f, 1f)

            // Les nuits d'Atys, sous tout le reste. Elles se comptent par heure
            // et non par cycle : un cycle de trois heures enjambe volontiers le
            // lever du jour, et l'ombrer en entier avancerait la nuit d'une
            // heure ou deux.
            val heurePremiere = cycles.first().cycle.toLong() * HEURES_PAR_CYCLE
            val parCycle = 1f / HEURES_PAR_CYCLE
            repeat(cycles.size * HEURES_PAR_CYCLE) { h ->
                if (estLaNuit((((heurePremiere + h) % 24 + 24) % 24).toInt())) {
                    drawRect(couleurNuit, Offset(x(h * parCycle), 0f),
                             Size(largeur * parCycle / cases, haut))
                }
            }

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

            // La courbe en marches et son aire : l'aire fait lire d'un coup les
            // creux, qui sont justement les bonnes fenêtres.
            val trace = Path()
            val aire = Path()
            aire.moveTo(x(0f), haut)
            cycles.forEachIndexed { i, m ->
                val gauche = x(i.toFloat())
                val droite = x(i + 1f)
                val py = y(m.value)
                if (i == 0) trace.moveTo(gauche, py) else trace.lineTo(gauche, py)
                trace.lineTo(droite, py)
                aire.lineTo(gauche, py)
                aire.lineTo(droite, py)
            }
            aire.lineTo(x(cases), haut)
            aire.close()
            drawPath(aire, remplissage)
            drawPath(trace, couleurCourbe, style = Stroke(width = 3.5f))

            // Le trait du « maintenant », posé à l'intérieur du cycle en cours :
            // l'API donne l'heure d'Atys avec ses décimales, autant s'en servir.
            val iMaintenant = cycles.indexOfFirst { it.cycle == releve.cycleCourant }
            if (iMaintenant >= 0) {
                val px = x(iMaintenant + releve.avancementDuCycle.toFloat())
                drawLine(couleurMaintenant, Offset(px, 0f), Offset(px, haut),
                         strokeWidth = 2f)
            }
            drawLine(couleurAxe, Offset(margeGauche, haut), Offset(size.width, haut),
                     strokeWidth = 1f)

            // L'heure réelle, à chaque heure ronde : les étiquettes se posent au
            // temps qu'elles annoncent, non au cycle le plus proche — un cycle
            // vaut neuf minutes, et six cycles font cinquante-quatre minutes,
            // pas une heure.
            if (iMaintenant >= 0) {
                val maintenant = LocalTime.now()
                val minutesAvant =
                    (iMaintenant + releve.avancementDuCycle.toFloat()) * MINUTES_PAR_CYCLE
                val depart = maintenant.minusMinutes(minutesAvant.toLong())
                val totalMinutes = cycles.size * MINUTES_PAR_CYCLE
                var heure = depart.truncatedTo(java.time.temporal.ChronoUnit.HOURS)
                if (heure.isBefore(depart)) heure = heure.plusHours(1)
                var decalage = minutesEntre(depart, heure)
                while (decalage < totalMinutes) {
                    val px = (x(decalage / MINUTES_PAR_CYCLE.toFloat()) - 16f)
                        .coerceIn(0f, size.width - 34f)
                    etiquette(mesure, heure.format(HEURE), Offset(px, haut + 4f),
                              couleurTexte)
                    heure = heure.plusHours(1)
                    decalage += 60f
                }
            }
        }
    }
}

/** Minutes de `depuis` à `vers`, la seconde heure étant toujours la plus tardive. */
private fun minutesEntre(depuis: LocalTime, vers: LocalTime): Float {
    val ecart = (vers.toSecondOfDay() - depuis.toSecondOfDay()) / 60f
    return if (ecart < 0f) ecart + 24 * 60 else ecart
}

private val HEURE: DateTimeFormatter = DateTimeFormatter.ofPattern("HH'h'")

private fun androidx.compose.ui.graphics.drawscope.DrawScope.etiquette(
    mesure: TextMeasurer, texte: String, position: Offset, couleur: Color,
) {
    drawText(mesure, texte, position,
             style = TextStyle(color = couleur, fontSize = 10.sp))
}
