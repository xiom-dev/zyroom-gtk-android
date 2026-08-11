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
    fun `ne retient que les items et les codes de compétences`() {
        val data = "STR_PACK".toByteArray() +
            record("uxt_bidule.string", "Autre chose", 2) +
            record("iasl.sitem", "Mektoub de monte", 2) +
            record("sfms", "Manier épée", 2)
        val db = NameDb.parse(data)
        assertEquals(2, db.size)
        assertEquals("Mektoub de monte", db.nameOf("iasl.sitem"))
        // Le flux personnage ne nomme les compétences que par ces codes.
        assertEquals("Manier épée", db.nameOf("sfms"))
    }

    /**
     * Un enregistrement fantôme ne doit pas avaler le vrai qui le suit.
     *
     * Le pack se lit en avançant d'enregistrement en enregistrement, et en
     * cherchant octet par octet quand l'un ne se présente pas. Rien
     * n'empêchait alors une suite d'octets quelconque de ressembler à un
     * enregistrement : celui qui commençait à l'intérieur était perdu. Ici
     * la fausse clé contient un octet accentué, ce qu'aucune clé n'a.
     */
    @Test
    fun `un faux enregistrement ne fait pas perdre le suivant`() {
        val leurre = byteArrayOf(4, 0, 0, 0) + byteArrayOf(0xE9.toByte(), 0x21, 0x21, 0x21) +
            byteArrayOf(2) + intLE(200)     // annonce deux cents octets de valeur
        val data = "STR_PACK".toByteArray() + leurre +
            record("m0117dxajd01.sitem", "Ambre de choix", 2)
        assertEquals("Ambre de choix", NameDb.parse(data).nameOf("m0117dxajd01.sitem"))
    }

    /**
     * Le pack livré avec l'application : tout l'arbre des compétences doit s'y
     * nommer, des quatre racines aux feuilles les plus profondes.
     */
    @Test
    fun `le pack livré nomme les compétences`() {
        val pack = File("src/main/assets/string_client.pack")
        assumeTrue("pack livré absent", pack.isFile)
        val db = NameDb.read(pack)
        assertEquals("Combat", db.nameOf("sf"))
        assertEquals("Magie", db.nameOf("sm"))
        assertEquals("Artisanat", db.nameOf("sc"))
        assertEquals("Extraire les matières premières", db.nameOf("sh"))
        assertEquals("Expert en création de manches lourdes", db.nameOf("scahse"))
        assertEquals("Maître en magie élémentaire", db.nameOf("smoeaem"))
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

    /**
     * Les accents, du pack jusqu'à l'écran.
     *
     * Le pack du jeu compte 26 254 noms, dont **12 680 accentués**, et il les
     * range tous en UTF-16 : la longueur y est un nombre de caractères, et
     * chacun vaut deux octets. Le format UTF-8, que le code sait lire aussi,
     * n'apparaît dans aucun enregistrement du pack réel — il est gardé pour un
     * format que le jeu pourrait employer, et compté en octets.
     */
    @Test
    fun `les accents traversent les deux formats`() {
        val db = NameDb.parse(
            record("abcbahp.sitem", "Plan de jambières Erouk'an", 1) +
            record("aaa.sitem", "Écorce d'Amberité — Sève « supérieure »", 2))
        assertEquals("Plan de jambières Erouk'an", db.nameOf("abcbahp.sitem"))
        assertEquals("Écorce d'Amberité — Sève « supérieure »", db.nameOf("aaa.sitem"))
    }
}
