package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.model.Entity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * La forme des clés et l'appel groupé, tels que la documentation de l'API les
 * décrit : « API keys are 41 alphanumeric characters. Character keys start with
 * 'c' and guild keys with 'g'. »
 */
class ApiKeyTest {

    // Clés fabriquées, jamais de vraies : une clé d'API dans un dépôt donne un
    // accès en lecture aux inventaires qu'elle couvre, et l'historique git la
    // garde bien après qu'on l'en a retirée.
    private val cleGuilde = "g" + "0".repeat(40)
    private val clePerso = "c" + "0".repeat(40)

    @Test
    fun `une clé fait 41 caractères et commence par c ou g`() {
        assertTrue(RyzomApi.isApiKey(cleGuilde))
        assertTrue(RyzomApi.isApiKey(clePerso))
        assertFalse("trop courte", RyzomApi.isApiKey("c123"))
        assertFalse("mauvaise initiale", RyzomApi.isApiKey("x" + "0".repeat(40)))
        assertFalse("caractère interdit", RyzomApi.isApiKey("c-" + "0".repeat(39)))
    }

    @Test
    fun `la première lettre dit l'espèce`() {
        assertEquals(Entity.Kind.GUILD, RyzomApi.kindOf(cleGuilde))
        assertEquals(Entity.Kind.CHARACTER, RyzomApi.kindOf(clePerso))
        assertNull(RyzomApi.kindOf("zzz"))
    }

    @Test
    fun `plusieurs clés tiennent dans un seul appel`() {
        val url = RyzomApi.charactersUrl(listOf("c1", "c2"))
        assertEquals("https://api.ryzom.com/character.php?apikey%5B%5D=c1&apikey%5B%5D=c2",
                     url)
    }

    @Test
    fun `un flux à plusieurs personnages les rend tous, rangés par clé`() {
        val flux = """
            <?xml version="1.0"?>
            <ryzomapi>
              <character apikey="c1" created="1" cached_until="2">
                <id>1</id><name>Xiom</name><bag/>
              </character>
              <character apikey="c2" created="1" cached_until="2">
                <id>2</id><name>Autre</name><bag/>
              </character>
            </ryzomapi>
        """.trimIndent().toByteArray()

        val entites = EntityParser.parseAll(flux, Entity.Kind.CHARACTER)
        assertEquals(setOf("c1", "c2"), entites.keys)
        assertEquals("Xiom", entites["c1"]?.name)
        assertEquals("Autre", entites["c2"]?.name)
    }

    @Test
    fun `une clé refusée n'empêche pas les autres d'arriver`() {
        val flux = """
            <?xml version="1.0"?>
            <ryzomapi>
              <character apikey="c1"><error code="3">Invalid apikey</error></character>
              <character apikey="c2" created="1" cached_until="2">
                <id>2</id><name>Autre</name><bag/>
              </character>
            </ryzomapi>
        """.trimIndent().toByteArray()

        val entites = EntityParser.parseAll(flux, Entity.Kind.CHARACTER)
        assertEquals(setOf("c2"), entites.keys)
    }
}
