package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Les noms de bêtes tels que le jeu les écrit, relevés dans le flux d'un vrai
 * personnage : une chaîne unique qui porte toutes les traductions.
 */
class CreatureNameTest {

    @Test
    fun `garde le français quand il est là`() {
        assertEquals(
            "Zig de Xiom",
            EntityParser.cleanName("$#[wk]Xiom's Zig[fr]Zig de Xiom"),
        )
    }

    @Test
    fun `retire les dollars qui encadrent`() {
        assertEquals("Zig Yubo Premium",
                     EntityParser.cleanName("Zig Yubo Premium$"))
    }

    @Test
    fun `prend le premier segment faute de français`() {
        assertEquals("Xiom's Zig",
                     EntityParser.cleanName("$#[wk]Xiom's Zig[de]Xioms Zig"))
    }

    @Test
    fun `laisse tranquille un nom ordinaire`() {
        assertEquals("Mounty", EntityParser.cleanName("Mounty"))
        assertEquals("", EntityParser.cleanName("  "))
    }
}
