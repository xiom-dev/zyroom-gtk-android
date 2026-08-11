package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Les bêtes du joueur, et où elles sont.
 *
 * Le flux donne leur position ; c'est la seule chose que l'API sache dire d'un
 * mektoub qu'on ne retrouve plus.
 */
class BeteTest {

    private val flux = """
        <?xml version="1.0"?><ryzomapi><character created="1" cached_until="2">
        <id>689325</id><name>Xiom</name><pets>
          <animal index="0"><sheet>gubani_mount_03.creature</sheet>
            <status>landscape</status><satiety>701.68</satiety><name>Mounty</name>
            <position x="10328" y="-2316" z="-97"/><inventory/></animal>
          <animal index="1"><sheet>chjjf3.creature</sheet>
            <status>stable</status><name></name><inventory/></animal>
          <animal index="2"><sheet>chxjf_zig.creature</sheet>
            <status>landscape</status><satiety>54</satiety>
            <name>${'$'}#[wk]Xiom's Zig[fr]Zig de Xiom</name>
            <position x="9721" y="-2594" z="-9"/><inventory/></animal>
        </pets></character></ryzomapi>
    """.trimIndent()

    private val betes get() = EntityParser.parseCharacter(flux.toByteArray()).betes

    @Test
    fun `chaque bête porte sa position et son étiquette`() {
        val mounty = betes.first { it.nom == "Mounty" }
        assertEquals(10328, mounty.x)
        assertEquals(-2316, mounty.y)
        assertEquals("Monture 1", mounty.etiquette)
        assertTrue(mounty.dehors)
    }

    /** Le nom est une chaîne multilingue : sans décodage, c'est illisible. */
    @Test
    fun `le nom donné en jeu est décodé`() {
        assertEquals("Zig de Xiom", betes.first { it.etiquette == "Zig 1" }.nom)
    }

    /** Une bête à l'écurie est là où on l'a rangée : sa position ne dit rien. */
    @Test
    fun `une bête sans position ne prétend pas en avoir une`() {
        val rangee = betes.first { it.etiquette == "Mektoub 1" }
        assertFalse(rangee.dehors)
        assertEquals(0, rangee.x)
    }

    @Test
    fun `la satiété est rendue telle quelle`() {
        assertEquals(54.0, betes.first { it.etiquette == "Zig 1" }.satiete, 0.01)
    }

    /**
     * Le jeu écrit ses espaces insécables en UTF-8 relu comme du latin-1.
     *
     * Sans réparation, le nom se lisait « Zig<Â> de<Â> Xiom » — l'ancien
     * décodage retirait l'espace mais laissait le « Â ».
     */
    @Test
    fun `le double encodage du jeu est réparé`() {
        assertEquals("Zig de Xiom",
                     EntityParser.cleanName("${'$'}#[wk]Xiom's\u00C2\u00A0Zig" +
                                            "[fr]Zig\u00C2\u00A0de\u00C2\u00A0Xiom"))
    }

    /** Un nom qui porte légitimement un « Â » ne doit pas être abîmé. */
    @Test
    fun `un accent véritable survit`() {
        assertEquals("Bête à Â", EntityParser.cleanName("Bête à Â"))
    }

    /**
     * La position du personnage lui-même, à la racine du flux.
     *
     * Elle y est depuis toujours et personne ne la lisait. C'est celle de sa
     * dernière déconnexion, pas un suivi en direct — mais elle donne le repère
     * qui manquait sur la carte : à quelle distance de ses bêtes on se trouve.
     */
    @Test
    fun `le personnage porte sa propre position`() {
        val flux = """
            <?xml version="1.0"?><ryzomapi><character><id>689325</id>
            <name>Xiom</name><position x="10064" y="-2604" z="-77"/>
            <pets/></character></ryzomapi>
        """.trimIndent()
        val perso = EntityParser.parseCharacter(flux.toByteArray())
        assertEquals(10064, perso.x)
        assertEquals(-2604, perso.y)
    }

    /** Sans position, on ne prétend pas en avoir une. */
    @Test
    fun `un personnage sans position vaut zéro`() {
        val flux = """
            <?xml version="1.0"?><ryzomapi><character><id>1</id><name>X</name>
            </character></ryzomapi>
        """.trimIndent()
        assertEquals(0, EntityParser.parseCharacter(flux.toByteArray()).x)
    }
}
