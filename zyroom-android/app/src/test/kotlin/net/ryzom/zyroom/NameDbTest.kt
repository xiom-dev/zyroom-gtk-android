package net.ryzom.zyroom

import net.ryzom.zyroom.names.NameDb
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.io.File

/** Le lecteur de `string_client.pack` doit accepter les deux formats. */
class NameDbTest {

    private fun record(key: String, value: String, separator: Int): ByteArray {
        val out = ByteArrayOutputStream()
        val keyBytes = key.toByteArray(Charsets.ISO_8859_1)
        out.write(intLE(keyBytes.size))
        out.write(keyBytes)
        out.write(separator)
        val valueBytes = if (separator == 1) value.toByteArray(Charsets.UTF_16LE)
                         else value.toByteArray(Charsets.UTF_8)
        val count = if (separator == 1) value.length else valueBytes.size
        out.write(intLE(count))
        out.write(valueBytes)
        return out.toByteArray()
    }

    private fun intLE(value: Int) = byteArrayOf(
        value.toByte(), (value shr 8).toByte(),
        (value shr 16).toByte(), (value shr 24).toByte())

    @Test
    fun `lit l'ancien format en UTF-16`() {
        val data = "STR_PACK".toByteArray() +
            record("m0117dxajd01.sitem", "Ambre de choix / Sha de la Jungle", 1)
        val db = NameDb.parse(data)
        assertEquals("Ambre de choix / Sha de la Jungle",
                     db.nameOf("m0117dxajd01.sitem"))
    }

    @Test
    fun `lit le format récent en UTF-8`() {
        val data = "STR_PACK".toByteArray() +
            record("amber_cube_common_ancient.sitem", "Cube d'ambre ancien", 2)
        val db = NameDb.parse(data)
        assertEquals("Cube d'ambre ancien",
                     db.nameOf("amber_cube_common_ancient.sitem"))
    }

    @Test
    fun `une fiche inconnue rend son identifiant`() {
        assertEquals("inconnu.sitem", NameDb.EMPTY.nameOf("inconnu.sitem"))
    }

    @Test
    fun `ne retient que les fiches d'items`() {
        val data = "STR_PACK".toByteArray() +
            record("uxt_bidule.string", "Autre chose", 2) +
            record("iasl.sitem", "Mektoub de monte", 2)
        val db = NameDb.parse(data)
        assertEquals(1, db.size)
        assertEquals("Mektoub de monte", db.nameOf("iasl.sitem"))
    }

    /**
     * Le vrai pack du poste de développement, quand il est là : c'est le seul
     * test qui prouve que le lecteur tient devant les trois mégaoctets réels.
     */
    @Test
    fun `lit le pack du client, s'il est disponible`() {
        val pack = File(System.getProperty("user.home"),
                        ".local/share/Ryzom/0/save/string_client.pack")
        assumeTrue("pack absent", pack.isFile)
        val db = NameDb.read(pack)
        assertTrue("au moins mille fiches", db.size > 1000)
        assertEquals("Ambre de choix / Sha de la Jungle",
                     db.nameOf("m0117dxajd01.sitem"))
    }
}
