package net.ryzom.zyroom.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

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
    background = Fond,
    onBackground = Color(0xFFE2E8E6),
    surface = Surface,
    onSurface = Color(0xFFE2E8E6),
    surfaceVariant = Color(0xFF1E2C31),
    onSurfaceVariant = Color(0xFFBCC8C6),
    error = Color(0xFFE2696A),
)

@Composable
fun ZyRoomTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = couleurs, content = content)
}
