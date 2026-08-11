package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * L'analyseur, sur un vrai flux du jeu et non sur un extrait écrit à la main.
 *
 * Un extrait minimal ne prouve que ce qu'on y a mis. Ce document-ci est celui
 * d'un personnage réel : sept bêtes, deux cent soixante balises distinctes, et
 * des champs qu'on ne lit pas encore.
 */
class FluxReelTest {

    private val flux = javaClass.getResourceAsStream("/perso-reel.xml")!!.readBytes()

    @Test
    fun `la position du personnage se lit dans un vrai flux`() {
        val perso = EntityParser.parseCharacter(flux)
        assertEquals(10064, perso.x)
        assertEquals(-2604, perso.y)
    }

    @Test
    fun `les bêtes se lisent dans un vrai flux`() {
        val betes = EntityParser.parseCharacter(flux).betes
        assertEquals(7, betes.size)
        assertTrue(betes.any { it.nom == "Mounty" && it.x == 10328 })
        assertTrue(betes.any { it.nom == "Zig de Xiom" })
    }
}
