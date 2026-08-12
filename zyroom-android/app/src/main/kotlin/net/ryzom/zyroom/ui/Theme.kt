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
 * La capitale du titre : Cinzel Decorative, une romaine gravée.
 *
 * Le V de la gothique se confond avec un U — c'est le défaut du dessin, pas de
 * la lecture. Cette capitale-là, inspirée des inscriptions romaines, le tranche
 * nettement tout en restant du même monde que le reste du titre.
 *
 * Libre sous SIL Open Font License 1.1, texte dans `licenses/` et dans l'APK,
 * comme pour Pirata One. « Cinzel » est un Reserved Font Name.
 */
val Capitale = FontFamily(Font(R.font.cinzel_decorative))

/**
 * Les nuances d'orange du coffre, de la lumière du couvercle à son ombre.
 *
 * Relevées sur l'icône de l'application — le brun clair du dessus, le cuivre du
 * milieu, la terre du bas — puis éclaircies juste assez pour se lire sur le
 * fond sombre. Elles servent à distinguer les sous-branches de l'arbre des
 * compétences les unes des autres : six suffisent, aucune branche n'ayant plus
 * de six enfants.
 */
val OrangesDuCoffre = listOf(
    Color(0xFFF5B85C), Color(0xFFE89446), Color(0xFFDA7539),
    Color(0xFFC95C35), Color(0xFFB8492F), Color(0xFFF7D488),
)

/**
 * Le vert clair des petites icônes posées sur fond sombre.
 *
 * Le sarcelle du thème est fait pour de larges aplats ; réduit à une loupe de
 * vingt points, il s'éteint à côté des émojis voisins, qui sont dessinés par le
 * système en couleurs vives. Celui-ci est le même vert, éclairci de ce qu'il
 * faut pour tenir son rang dans la rangée — et il reste lisible quand la puce
 * est sélectionnée et que son fond devient vert sombre.
 */
val VertClair = Color(0xFF6FCBAA)

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
