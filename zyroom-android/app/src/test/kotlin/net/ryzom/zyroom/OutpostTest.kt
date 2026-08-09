package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.data.OutpostStore
import net.ryzom.zyroom.names.NameDb
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * L'annuaire public des guildes, et le journal des changements de main.
 *
 * `guilds.php` est la seule source publique sur les avant-postes : le flux
 * d'une guilde ne dit rien des autres, et il faut sa clé pour l'obtenir.
 */
class OutpostTest {

    private val annuaire = """
        <?xml version="1.0"?>
        <guilds version="1.0">
          <cache created="1" expire="61"/>
          <shard>atys</shard>
          <guild><gid>1</gid><name>La Lune Eternelle</name><icon>42</icon>
            <outposts>
              <outpost>fyros_outpost_04</outpost>
              <outpost>zorai_outpost_15</outpost>
            </outposts>
          </guild>
          <guild><gid>2</gid><name>Sans rien</name><icon>7</icon><outposts/></guild>
          <guild><gid>3</gid><name>Synoeca</name><icon>9</icon>
            <outposts><outpost>matis_outpost_17</outpost></outposts>
          </guild>
        </guilds>
    """.trimIndent().toByteArray()

    @Test
    fun `l'annuaire rend qui tient quoi`() {
        val carte = EntityParser.parseOutposts(annuaire)
        assertEquals(3, carte.size)
        // Les guildes sans avant-poste — l'immense majorité — ne laissent rien.
        assertTrue(carte.none { it.guild == "Sans rien" })

        val lune = carte.filter { it.guild == "La Lune Eternelle" }
        assertEquals(listOf("fyros_outpost_04", "zorai_outpost_15"), lune.map { it.code })
        assertEquals("42", lune.first().icon)
        // Le peuple se lit dans le code, et le nom se cherche avec un suffixe.
        assertEquals("fyros", lune.first().people)
        assertEquals("fyros_outpost_04.outpost", lune.first().nameKey)
    }

    private val store = OutpostStore(File("/dev/null"))

    @Test
    fun `une prise, une perte et une reprise se distinguent`() {
        val avant = mapOf(
            "a" to "La Lune Eternelle",     // gardé
            "b" to "La Lune Eternelle",     // perdu, personne ne le reprend
            "c" to "Synoeca",               // repris par une autre guilde
        )
        val apres = mapOf(
            "a" to "La Lune Eternelle",
            "c" to "La Lune Eternelle",
            "d" to "Al Kashi",              // pris à personne
        )
        val changements = store.diff(avant, apres).associateBy { it.outpost }

        assertEquals(3, changements.size)
        assertTrue("a n'a pas bougé", "a" !in changements)

        assertTrue(changements["b"]!!.lost)
        assertEquals("La Lune Eternelle", changements["b"]!!.from)

        assertEquals("Synoeca", changements["c"]!!.from)
        assertEquals("La Lune Eternelle", changements["c"]!!.to)
        assertTrue("un transfert n'est ni une prise ni une perte",
                   !changements["c"]!!.taken && !changements["c"]!!.lost)

        assertTrue(changements["d"]!!.taken)
        assertEquals("Al Kashi", changements["d"]!!.to)
    }

    @Test
    fun `un état identique ne journalise rien`() {
        val etat = mapOf("a" to "La Lune Eternelle")
        assertTrue(store.diff(etat, etat).isEmpty())
    }

    /**
     * Sur le vrai annuaire, quand la version GTK l'a mis en cache : les noms
     * des avant-postes doivent sortir du pack livré, sans quoi l'écran
     * n'afficherait que des identifiants.
     */
    @Test
    fun `sur le vrai annuaire, les avant-postes se nomment`() {
        val flux = File(System.getProperty("user.home"),
                        ".cache/zyroom-gtk/guild/105906237.xml")
        assumeTrue("aucun flux de guilde en cache", flux.isFile)
        val pack = File("src/main/assets/string_client.pack")
        assumeTrue("pack absent", pack.isFile)

        val noms = NameDb.read(pack)
        val guilde = EntityParser.parseGuild(flux.readBytes())
        assumeTrue("pas d'avant-poste dans ce flux", guilde.name.isNotEmpty())

        // Le pack nomme bien les avant-postes, suffixe compris.
        assertEquals("Ferme de Malmontagne", noms.nameOf("fyros_outpost_04.outpost"))
        assertEquals("Forteresse du Tourbillon", noms.nameOf("tryker_outpost_31.outpost"))
    }
}
