package net.ryzom.zyroom.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import net.ryzom.zyroom.R

/**
 * Thème sombre, dans les teintes du logo de ZyRoom : le sarcelle du coffre et
 * l'or de ses ferrures. Sombre en toutes circonstances — on consulte ses
 * inventaires en jouant, souvent le soir.
 */
private val Sarcelle = Color(0xFF3F7A68)
private val SarcelleSombre = Color(0xFF2B5648)
private val Or = Color(0xFFE8C15A)
private val Fond = Color(0xFF10171A)
private val Surface = Color(0xFF172226)

private val couleurs = darkColorScheme(
    primary = Sarcelle,
    onPrimary = Color(0xFF06120E),
    primaryContainer = SarcelleSombre,
    onPrimaryContainer = Color(0xFFD6EDE4),
    secondary = Or,
    onSecondary = Color(0xFF231A05),
    // Ce que Material peint quand une puce est sélectionnée. Non défini, il
    // retombait sur le mauve de la palette par défaut, étranger au logo : les
    // coffres choisis et le tri actif tranchaient avec le reste.
    secondaryContainer = SarcelleSombre,
    onSecondaryContainer = Color(0xFFD6EDE4),
    background = Fond,
    onBackground = Color(0xFFE2E8E6),
    surface = Surface,
    onSurface = Color(0xFFE2E8E6),
    surfaceVariant = Color(0xFF1E2C31),
    onSurfaceVariant = Color(0xFFBCC8C6),
    error = Color(0xFFE2696A),
)

/**
 * Le lettrage du titre : Pirata One, une gothique de bois gravé.
 *
 * Police libre sous SIL Open Font License 1.1, dont le texte est dans
 * `licenses/OFL-PirataOne.txt` — la licence oblige à la transmettre avec la
 * police, ce que fait l'APK qui l'embarque. Le nom « Pirata » est un Reserved
 * Font Name : le fichier ne doit pas être renommé pour désigner une version
 * modifiée.
 */
val Titrage = FontFamily(Font(R.font.pirata_one))

/**
 * Le fond d'une ligne sur deux, dans les listes qui se lisent en travers.
 *
 * Le vert de l'application, très dilué : sur des colonnes étroites l'œil perd
 * sa ligne, et une teinte alternée la tient mieux qu'un filet, qui hachait la
 * lecture à chaque rang. Défini ici, et non recopié dans chaque écran, pour que
 * « le même zébrage » le reste.
 */
@Composable
fun fondZebre(pair: Boolean): Color =
    if (pair) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.22f)
    else Color.Transparent

@Composable
fun ZyRoomTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = couleurs, content = content)
}
