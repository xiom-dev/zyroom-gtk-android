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
 * Il n'est écrit dans aucune documentation : il a été retrouvé en cherchant
 * dans l'image une vue dont on connaissait le centre et l'échelle. Ces essais
 * gardent le résultat, faute de quoi une régénération de la carte pourrait le
 * décaler sans que rien ne le signale.
 *
 * Ils ne valent que pour les variantes qui embarquent la carte : celle de
 * F-Droid ne l'a pas, et ce fichier n'y est pas compilé.
 */
class CarteAtysTest {

    @Test
    fun `un point connu tombe au bon pixel`() {
        // Mounty, la monture de Xiom, dans le Pays Malade.
        assertEquals(843.2f, CarteAtys.x(10328), 0.1f)
        assertEquals(2038.4f, CarteAtys.y(-2316), 0.1f)
    }

    @Test
    fun `le coin haut-gauche est l'origine`() {
        assertEquals(0f, CarteAtys.x(CarteAtys.X0), 0.01f)
        assertEquals(0f, CarteAtys.y(CarteAtys.Y0), 0.01f)
    }

    /** Hors de la carte, on ne montre rien plutôt qu'un marqueur au bord. */
    @Test
    fun `ce qui sort de la carte est écarté`() {
        assertFalse(CarteAtys.contient(0, 0))
        assertFalse(CarteAtys.contient(30000, -2000))
        assertTrue(CarteAtys.contient(10328, -2316))
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
