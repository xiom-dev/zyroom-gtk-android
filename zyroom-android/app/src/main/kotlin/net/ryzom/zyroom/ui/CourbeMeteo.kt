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
import androidx.compose.ui.graphics.drawscope.clipRect
import androidx.compose.ui.text.TextMeasurer
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import net.ryzom.zyroom.model.HEURES_PAR_CYCLE
import net.ryzom.zyroom.model.MINUTES_PAR_HEURE_ATYS
import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.estLaNuit
import java.time.LocalTime
import java.time.format.DateTimeFormatter

/**
 * Ce que la courbe montre, en heures d'Atys, et où s'y tient le présent.
 *
 * Vingt-quatre heures d'Atys valent soixante-douze minutes réelles : de quoi
 * voir une heure d'avance et un bon quart d'heure de passé. Le trait du présent
 * se tient à un sixième de la largeur — c'est ce qui vient qui compte, le passé
 * ne sert qu'à comprendre d'où l'on sort. Pas contre le bord pour autant : on
 * veut encore voir le palier qu'on quitte.
 */
private const val FENETRE_HEURES = 24.0
private const val ANCRE = 0.15

/**
 * L'humidité dans le temps, **en marches d'escalier**.
 *
 * Le jeu ne fait pas varier la météo en continu : une valeur vaut pour tout un
 * cycle — trois heures d'Atys, neuf minutes réelles — puis saute à la suivante.
 * Relier les points par des obliques dessinait des crêtes qui n'existent pas et
 * déplaçait les moments intéressants : la fenêtre excellente n'est pas un
 * sommet qu'on rate, c'est un palier qui dure.
 *
 * **C'est le graphique qui défile, pas le trait.** Le présent se tient près du
 * bord gauche et la courbe glisse dessous, comme un sismographe : on garde
 * ainsi toujours la même avance sous les yeux, au lieu de voir le trait dériver
 * vers le bord jusqu'à sortir de la vue.
 *
 * Les trois traits en pointillé sont les seuils du jeu — 16,66 %, 50 % et
 * 83,33 % — qui découpent les quatre conditions de gisement : sous le premier,
 * c'est excellent. Les bandes sombres sont les nuits d'Atys, que le jeu compte
 * de 22 h à 3 h : ce sont elles qui décident des matières excellentes de nuit.
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

            // Tout se repère en heures d'Atys, et non en indices de cycle :
            // c'est ce qui permet à la fenêtre de glisser continûment sous un
            // trait fixe, au lieu de sauter de trois heures en trois heures.
            val gauche = releve.heureAtys - ANCRE * FENETRE_HEURES
            fun x(heure: Double) =
                margeGauche + largeur * ((heure - gauche) / FENETRE_HEURES).toFloat()
            fun y(valeur: Double) = haut * (1f - valeur.toFloat()).coerceIn(0f, 1f)

            clipRect(left = margeGauche, top = 0f, right = size.width, bottom = haut) {
                // Les nuits, comptées par heure et non par cycle : un cycle de
                // trois heures enjambe volontiers le lever du jour.
                val largeurHeure = largeur / FENETRE_HEURES.toFloat()
                var heure = gauche.toLong() - 1
                while (heure < gauche + FENETRE_HEURES + 2) {
                    if (estLaNuit(((heure % 24 + 24) % 24).toInt())) {
                        drawRect(couleurNuit, Offset(x(heure.toDouble()), 0f),
                                 Size(largeurHeure, haut))
                    }
                    heure++
                }

                // La courbe en marches et son aire : l'aire fait lire d'un coup
                // les creux, qui sont justement les bonnes fenêtres. Un cycle
                // couvre trois heures : son palier va de `cycle * 3` à
                // `(cycle + 1) * 3`.
                val trace = Path()
                val aire = Path()
                aire.moveTo(x(cycles.first().cycle * HEURES_PAR_CYCLE.toDouble()), haut)
                cycles.forEachIndexed { i, m ->
                    val debut = x(m.cycle * HEURES_PAR_CYCLE.toDouble())
                    val fin = x((m.cycle + 1) * HEURES_PAR_CYCLE.toDouble())
                    val py = y(m.value)
                    if (i == 0) trace.moveTo(debut, py) else trace.lineTo(debut, py)
                    trace.lineTo(fin, py)
                    aire.lineTo(debut, py)
                    aire.lineTo(fin, py)
                }
                aire.lineTo(x((cycles.last().cycle + 1) * HEURES_PAR_CYCLE.toDouble()), haut)
                aire.close()
                drawPath(aire, remplissage)
                drawPath(trace, couleurCourbe, style = Stroke(width = 3.5f))
            }

            // Les seuils, par-dessus la courbe, et leur étiquette dans la marge.
            val pointille = PathEffect.dashPathEffect(floatArrayOf(8f, 8f))
            listOf(0.1666f to "16", 0.5f to "50", 0.8333f to "83").forEach { (v, texte) ->
                val yy = y(v.toDouble())
                drawLine(couleurSeuil, Offset(margeGauche, yy), Offset(size.width, yy),
                         strokeWidth = 1.5f, pathEffect = pointille)
                etiquette(mesure, texte, Offset(0f, (yy - 14f).coerceAtLeast(0f)),
                          couleurTexte)
            }

            // Le présent, immobile près du bord gauche.
            val px = x(releve.heureAtys)
            drawLine(couleurMaintenant, Offset(px, 0f), Offset(px, haut), strokeWidth = 2f)
            drawLine(couleurAxe, Offset(margeGauche, haut), Offset(size.width, haut),
                     strokeWidth = 1f)

            // L'heure réelle, toutes les demi-heures. Une heure d'Atys valant
            // trois minutes, la fenêtre ne couvre que soixante-douze minutes :
            // à l'heure ronde, il n'y aurait qu'un repère, parfois zéro.
            val maintenant = LocalTime.now()
            var repere = maintenant.withMinute(0).withSecond(0).withNano(0)
                .minusHours(1)
            repeat(8) {
                repere = repere.plusMinutes(30)
                val minutes = minutesEntre(maintenant, repere)
                val atys = releve.heureAtys + minutes / MINUTES_PAR_HEURE_ATYS
                if (atys in gauche..(gauche + FENETRE_HEURES)) {
                    val texte = if (repere.minute == 0) repere.format(HEURE)
                                else repere.format(HEURE_MINUTE)
                    etiquette(mesure, texte,
                              Offset((x(atys) - 20f).coerceIn(0f, size.width - 46f),
                                     haut + 4f), couleurTexte)
                }
            }
        }
    }
}

/** Minutes de `depuis` à `vers`, signées, en tenant compte du passage de minuit. */
private fun minutesEntre(depuis: LocalTime, vers: LocalTime): Double {
    var ecart = (vers.toSecondOfDay() - depuis.toSecondOfDay()) / 60.0
    if (ecart > 12 * 60) ecart -= 24 * 60
    if (ecart < -12 * 60) ecart += 24 * 60
    return ecart
}

private val HEURE: DateTimeFormatter = DateTimeFormatter.ofPattern("HH'h'")
private val HEURE_MINUTE: DateTimeFormatter = DateTimeFormatter.ofPattern("HH'h'mm")

private fun androidx.compose.ui.graphics.drawscope.DrawScope.etiquette(
    mesure: TextMeasurer, texte: String, position: Offset, couleur: Color,
) {
    drawText(mesure, texte, position,
             style = TextStyle(color = couleur, fontSize = 10.sp))
}
