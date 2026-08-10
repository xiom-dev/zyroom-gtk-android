package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.estLaNuit
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * La lecture du flux météo, et ce qu'on en déduit du temps qui passe.
 *
 * Un cycle vaut trois heures d'Atys, neuf minutes réelles ; l'API donne l'heure
 * d'Atys avec ses décimales, et c'est d'elles que dépendent les comptes à
 * rebours comme la place du trait « maintenant ».
 */
class MeteoTest {

    private val flux = """
        {"version":"1.0","hour":"104011.496","cycle":34670,
         "continents":{"terre":{
           "34670":{"cycle":34670,"condition":"good","value":"0.483","text":"uiFair"},
           "34671":{"cycle":34671,"condition":"best","value":"0.042","text":"uiFair"}}}}
    """.trimIndent()

    @Test
    fun `le flux rend le cycle, l'heure d'Atys et les continents`() {
        val (cycle, heure, continents) = EntityParser.parseWeather(flux)
        assertEquals(34670, cycle)
        assertEquals(104011.496, heure, 0.001)
        assertEquals(listOf(34670, 34671), continents["terre"]!!.map { it.cycle })
        assertEquals(0.483, continents["terre"]!!.first().value, 0.001)
    }

    /**
     * 104011,496 heures d'Atys au cycle 34670 : le cycle commence à 104010, on
     * est donc à la moitié. Compter en cycles pleins annonçait neuf minutes
     * d'attente là où il n'en restait plus que quatre.
     */
    @Test
    fun `l'avancement dans le cycle se lit dans les décimales de l'heure`() {
        val (cycle, heure, continents) = EntityParser.parseWeather(flux)
        val releve = MeteoAtys(cycle, heure, saison = 0, continents = continents)
        assertEquals(0.499, releve.avancementDuCycle, 0.01)
        assertEquals(19, releve.heureDuJour)
        assertFalse(releve.nuit)
    }

    @Test
    fun `la nuit d'Atys va de vingt-deux heures à trois heures`() {
        assertTrue(estLaNuit(22))
        assertTrue(estLaNuit(23))
        assertTrue(estLaNuit(0))
        assertTrue(estLaNuit(2))
        assertFalse(estLaNuit(3))
        assertFalse(estLaNuit(12))
        assertFalse(estLaNuit(21))
    }

    /** Une heure absente ne doit pas décaler le relevé : on retombe sur le cycle. */
    @Test
    fun `sans heure, le cycle fait foi`() {
        val (cycle, heure, _) = EntityParser.parseWeather(
            """{"cycle":100,"continents":{}}""")
        assertEquals(100, cycle)
        assertEquals(300.0, heure, 0.001)
        assertEquals(0.0, MeteoAtys(cycle, heure, 0, emptyMap()).avancementDuCycle, 0.001)
    }
}
