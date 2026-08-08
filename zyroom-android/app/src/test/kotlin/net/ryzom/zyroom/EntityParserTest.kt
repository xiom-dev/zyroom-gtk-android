package net.ryzom.zyroom

import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.model.ItemColor
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/** Lecture des flux de l'API, sur un document réduit puis sur un vrai. */
class EntityParserTest {

    private val fluxPersonnage = """
        <?xml version="1.0"?>
        <ryzomapi version="1.0">
          <character created="1785853247" cached_until="1785920366" modules="C01:C04">
            <id>689325</id>
            <name>Xiom</name>
            <shard>atys</shard>
            <money>123456</money>
            <guild><name>La Lune Eternelle</name></guild>
            <bag>
              <item id="7296518493940551377" slot="1">
                <sheet>m0117dxajd01.sitem</sheet>
                <quality>250</quality>
                <stack>3</stack>
                <locked>1</locked>
                <craftparameters><color>4</color></craftparameters>
              </item>
              <item id="42" slot="2">
                <sheet>iasl.sitem</sheet>
                <quality>1</quality>
                <stack>1</stack>
              </item>
            </bag>
            <room/>
          </character>
        </ryzomapi>
    """.trimIndent().toByteArray()

    @Test
    fun `lit le personnage, ses inventaires et ses items`() {
        val entity = EntityParser.parseCharacter(fluxPersonnage)

        assertEquals("Xiom", entity.name)
        assertEquals("atys", entity.shard)
        assertEquals("La Lune Eternelle", entity.guild)
        assertEquals(123456L, entity.dappers)
        assertEquals(listOf("bag", "room"), entity.inventories.map { it.key })

        val sac = entity.inventories.first()
        assertEquals(2, sac.items.size)

        val ambre = sac.items.first()
        assertEquals("m0117dxajd01.sitem", ambre.sheet)
        assertEquals(250, ambre.quality)
        assertEquals(3, ambre.stack)
        assertEquals(ItemColor.BLUE, ambre.color)
        assertTrue(ambre.locked)
    }

    @Test
    fun `une qualité de 1 est ramenée à zéro`() {
        val entity = EntityParser.parseCharacter(fluxPersonnage)
        assertEquals(0, entity.inventories.first().items[1].quality)
    }

    @Test
    fun `la fraîcheur vient de l'API`() {
        val entity = EntityParser.parseCharacter(fluxPersonnage)
        assertEquals(1785920366L, entity.cachedUntil)
        assertTrue(entity.isStale(1785920367L))
        assertTrue(!entity.isStale(1785900000L))
    }

    @Test
    fun `une erreur de l'API est remontée`() {
        val flux = """
            <?xml version="1.0"?>
            <ryzomapi><error code="3">Invalid apikey</error></ryzomapi>
        """.trimIndent().toByteArray()
        val erreur = assertThrows(ApiException::class.java) {
            EntityParser.parseCharacter(flux)
        }
        assertTrue(erreur.message!!.contains("Invalid apikey"))
    }

    @Test
    fun `les coffres de guilde prennent leur nom et leur capacité`() {
        val flux = """
            <?xml version="1.0"?>
            <ryzomapi>
              <guild created="1" cached_until="2">
                <gid>105906237</gid>
                <name>La Lune Eternelle</name>
                <chests>
                  <chest><name>Matières</name><bulkmax>1000</bulkmax></chest>
                  <chest><name>Armes</name><bulkmax>1000</bulkmax></chest>
                  <chest><name></name><bulkmax>0</bulkmax></chest>
                </chests>
                <room>
                  <item id="1" slot="3"><sheet>m0117dxajd01.sitem</sheet></item>
                  <item id="2" slot="501"><sheet>icoafm1pa.sitem</sheet></item>
                  <item id="3" slot="502"><sheet>icoafm1pb.sitem</sheet></item>
                </room>
              </guild>
            </ryzomapi>
        """.trimIndent().toByteArray()

        val guilde = EntityParser.parseGuild(flux)
        assertEquals("La Lune Eternelle", guilde.name)
        // Le troisième coffre n'existe pas : ni déclaré ni garni.
        assertEquals(listOf("Coffre 1 — Matières", "Coffre 2 — Armes"),
                     guilde.inventories.map { it.label })
        assertEquals(listOf(1, 2), guilde.inventories.map { it.items.size })
        assertEquals(1000, guilde.inventories.first().capacity)
    }

    @Test
    fun `le message du jour de la guilde est lu, entités comprises`() {
        val flux = """
            <?xml version="1.0"?>
            <ryzomapi>
              <guild created="1" cached_until="2">
                <gid>1</gid><name>La Lune Eternelle</name>
                <motd>un salon Linux a &#xE9;t&#xE9; rajout&#xE9; avec les tutos Discord</motd>
                <chests><chest><name>Matières</name><bulkmax>1000</bulkmax></chest></chests>
                <room><item id="1" slot="1"><sheet>a.sitem</sheet></item></room>
              </guild>
            </ryzomapi>
        """.trimIndent().toByteArray()

        // L'API écrit les accents en entités numériques ; le lecteur DOM les
        // résout, il n'y a rien à décoder à la main.
        assertEquals("un salon Linux a été rajouté avec les tutos Discord",
                     EntityParser.parseGuild(flux).motd)
    }

    @Test
    fun `un personnage n'a pas de message du jour`() {
        assertEquals("", EntityParser.parseCharacter(fluxPersonnage).motd)
    }

    /**
     * Le nom porte l'article et l'espace de fin, tels que l'API les rend : une
     * égalité stricte sur le nom en minuscules n'y répondait pas, et le masque
     * ne s'appliquait donc à rien. L'ancien test employait « Petit coffre de
     * Nizy », un nom assaini qui laissait passer le défaut.
     */
    private val fluxAvecCoffreMasque = """
        <?xml version="1.0"?>
        <ryzomapi>
          <guild created="1" cached_until="2">
            <gid>1</gid><name>La Lune Eternelle</name>
            <chests>
              <chest><name>Matières</name><bulkmax>1000</bulkmax></chest>
              <chest><name>Le petit coffre de Nizy </name><bulkmax>2500</bulkmax></chest>
            </chests>
            <room>
              <item id="1" slot="1"><sheet>a.sitem</sheet></item>
              <item id="2" slot="501"><sheet>b.sitem</sheet></item>
              <item id="3" slot="502"><sheet>c.sitem</sheet></item>
            </room>
          </guild>
        </ryzomapi>
    """.trimIndent().toByteArray()

    @Test
    fun `un coffre masqué garde sa place mais se présente vide`() {
        val guilde = EntityParser.parseGuild(fluxAvecCoffreMasque, masquer = true)
        // Le coffre reste dans la liste : le faire disparaître amenait les
        // joueurs à demander pourquoi il en manquait un.
        assertEquals(listOf("Coffre 1 — Matières", "Coffre 2 — Le petit coffre de Nizy"),
                     guilde.inventories.map { it.label })
        assertEquals(listOf(1, 0), guilde.inventories.map { it.items.size })
        // Nom et capacité restent affichés, seul le contenu manque.
        assertEquals(2500, guilde.inventories[1].capacity)
    }

    @Test
    fun `la variante dev montre le contenu du coffre masqué`() {
        val guilde = EntityParser.parseGuild(fluxAvecCoffreMasque, masquer = false)
        assertEquals(listOf(1, 2), guilde.inventories.map { it.items.size })
    }

    /**
     * Le vrai flux de la guilde, quand le cache de la version GTK est là :
     * c'est le seul endroit où le nom du coffre est celui que l'API rend
     * vraiment, avec son article et son espace de fin.
     */
    @Test
    fun `sur le vrai flux de guilde, le coffre masqué est présent mais vide`() {
        val flux = File(System.getProperty("user.home"),
                        ".cache/zyroom-gtk/guild/105906237.xml")
        assumeTrue("aucun flux de guilde en cache", flux.isFile)
        val octets = flux.readBytes()

        val guilde = EntityParser.parseGuild(octets, masquer = true)
        val dev = EntityParser.parseGuild(octets, masquer = false)

        // Même liste de coffres des deux côtés : seul le contenu change.
        assertEquals(guilde.inventories.map { it.label }, dev.inventories.map { it.label })

        val masque = guilde.inventories.first { "nizy" in it.label.lowercase() }
        val garni = dev.inventories.first { "nizy" in it.label.lowercase() }
        assertEquals(0, masque.items.size)
        assertTrue("le coffre devrait être garni côté dev", garni.items.isNotEmpty())
        assertEquals(masque.capacity, garni.capacity)

        // Le message du jour, tel que les officiers l'ont écrit en jeu.
        assertTrue("message du jour absent du vrai flux", guilde.motd.isNotBlank())
    }

    /**
     * Les autres tests passent le masquage en paramètre : ils prouvent que la
     * mécanique marche, pas que la variante compilée est réglée comme il faut.
     * Celui-ci appelle sans paramètre, donc sur le réglage de la variante.
     */
    @Test
    fun `la variante compilée applique son propre réglage`() {
        val guilde = EntityParser.parseGuild(fluxAvecCoffreMasque)
        val coffre = guilde.inventories.first { "nizy" in it.label.lowercase() }
        assertEquals(
            "variante compilée avec MASQUE_COFFRES=$MASQUE_COFFRES",
            MASQUE_COFFRES, coffre.items.isEmpty())
    }

    @Test
    fun `sur le vrai flux, la variante compilée applique son propre réglage`() {
        val flux = File(System.getProperty("user.home"),
                        ".cache/zyroom-gtk/guild/105906237.xml")
        assumeTrue("aucun flux de guilde en cache", flux.isFile)
        val guilde = EntityParser.parseGuild(flux.readBytes())
        val coffre = guilde.inventories.first { "nizy" in it.label.lowercase() }
        // Le coffre est là dans les deux cas ; seul son contenu dépend du réglage.
        assertTrue("le coffre doit rester dans la liste", coffre.capacity > 0)
        assertEquals(MASQUE_COFFRES, coffre.items.isEmpty())
    }

    @Test
    fun `le masque reconnaît les variantes d'écriture du nom`() {
        listOf("Le petit coffre de Nizy ", "petit coffre de nizy",
               "PETIT COFFRE DE NIZY", "Le Petit Coffre de Nïzy",
               "le  petit   coffre de nizy").forEach {
            assertTrue("devrait être masqué : $it", EntityParser.isHiddenChest(it))
        }
        listOf("Grand coffre de Nizy", "La Forge Lunaire", "").forEach {
            assertFalse("ne devrait pas l'être : $it", EntityParser.isHiddenChest(it))
        }
    }

    /**
     * Le document mis en cache par la version GTK, quand il est là : c'est le
     * seul test qui confronte le lecteur à un vrai flux, avec ses trois cent
     * quarante items et ses montures.
     */
    @Test
    fun `lit un vrai flux du cache de la version GTK, s'il est disponible`() {
        val dossier = File(System.getProperty("user.home"),
                           ".cache/zyroom-gtk/character")
        val flux = dossier.listFiles { f -> f.extension == "xml" }?.firstOrNull()
        assumeTrue("aucun flux en cache", flux != null)

        val entity = EntityParser.parseCharacter(flux!!.readBytes())
        assertTrue(entity.name.isNotEmpty())
        assertTrue(entity.inventories.isNotEmpty())
        assertTrue("des items", entity.inventories.sumOf { it.items.size } > 0)
    }
}
