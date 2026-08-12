package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.model.CarteAtys
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Le repère de la carte d'Atys, vérifié sur des points connus.
 *
 * Le repère vient des tables que Ballistic Mystix publie — `world.json` place
 * chaque continent sur la carte du monde, `server.json` donne ses bornes en
 * coordonnées de jeu — et non plus d'un calage fait à la main dans l'image.
 * Ces essais gardent le résultat, faute de quoi une régénération de la carte
 * pourrait le décaler sans que rien ne le signale.
 *
 * Ils ne valent que pour les variantes qui embarquent la carte : celle de
 * F-Droid ne l'a pas, et ce fichier n'y est pas compilé.
 */
class CarteAtysTest {

    @Test
    fun `un point connu tombe au bon pixel`() {
        // Mounty, la monture de Xiom, dans le Pays Malade zoraï.
        val (px, py) = CarteAtys.pixel(10328, -2316)!!
        assertEquals(844.0f, px, 0.5f)
        assertEquals(2039.2f, py, 0.5f)
    }

    /**
     * Chaque région a son origine, et c'est tout le sujet.
     *
     * Fairhaven est dans les Lacs, la monture dans la jungle : avec une origine
     * unique, l'une des deux tombait forcément à côté.
     */
    @Test
    fun `deux régions différentes ont deux repères différents`() {
        assertEquals("tryker", CarteAtys.regionDe(17410, -32849)?.nom)
        assertEquals("zorai", CarteAtys.regionDe(10328, -2316)?.nom)
        val (fx, fy) = CarteAtys.pixel(17410, -32849)!!
        assertEquals(2390.0f, fx, 0.5f)
        assertEquals(2493.8f, fy, 0.5f)
    }

    /** La plus petite région gagne : le Nexus est inclus dans les bornes matis. */
    @Test
    fun `la région la plus précise l'emporte`() {
        assertEquals("nexus", CarteAtys.regionDe(8700, -7000)?.nom)
    }

    /**
     * Les terres matis se placent — elles ne se plaçaient pas.
     *
     * L'origine matis calée à la main était celle de la jungle, à quatorze
     * mille unités de la vraie. Tout point de la forêt tombait alors en dehors
     * de l'image, et `pixel()` rendait `null` : **aucune bête laissée chez les
     * Matis n'apparaissait sur la carte**, sans le moindre message. C'est la
     * table publiée qui l'a révélé.
     */
    @Test
    fun `les terres matis se placent sur la carte`() {
        for (point in listOf(320 to -7840, 3280 to -4080, 6240 to -320)) {
            assertEquals("matis", CarteAtys.regionDe(point.first, point.second)?.nom)
            assertTrue("$point devrait tomber sur la carte",
                       CarteAtys.contient(point.first, point.second))
        }
    }

    /** Silan et les sous-terrains du Nexus sont venus avec la table publiée. */
    @Test
    fun `les régions ajoutées par la table publiée sont là`() {
        assertEquals("newbieland", CarteAtys.regionDe(9500, -11000)?.nom)
        assertTrue(CarteAtys.contient(9500, -11000))
        assertEquals(13, CarteAtys.REGIONS.size)
    }

    /** Hors de la carte, on ne montre rien plutôt qu'un marqueur au bord. */
    @Test
    fun `ce qui sort de la carte est écarté`() {
        assertFalse(CarteAtys.contient(0, 0))
        assertFalse(CarteAtys.contient(30000, -2000))
        assertTrue(CarteAtys.contient(10328, -2316))
        assertTrue(CarteAtys.contient(17410, -32849))
    }

    /** Une bête jamais sortie n'a pas de position : (0, 0) ne doit rien placer. */
    @Test
    fun `une bête sans position ne s'affiche pas`() {
        val flux = """
            <?xml version="1.0"?><ryzomapi><character><id>1</id><name>X</name>
            <pets><animal index="0"><sheet>chjjf3.creature</sheet>
            <status>stable</status><inventory/></animal></pets>
            </character></ryzomapi>
        """.trimIndent()
        val bete = EntityParser.parseCharacter(flux.toByteArray()).betes.single()
        assertFalse(CarteAtys.contient(bete.x, bete.y))
    }
}
