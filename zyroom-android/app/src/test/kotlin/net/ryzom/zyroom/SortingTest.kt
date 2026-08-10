package net.ryzom.zyroom

import net.ryzom.zyroom.model.Family
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.SortOrder
import net.ryzom.zyroom.model.familyOf
import net.ryzom.zyroom.model.materialKey
import net.ryzom.zyroom.model.outfitKey
import net.ryzom.zyroom.model.sortItems
import org.junit.Assert.assertEquals
import org.junit.Test

/** Le classement des objets, porté de `sorting.py`. */
class SortingTest {

    private fun item(sheet: String, quality: Int = 0, stack: Int = 1) =
        Item(sheet = sheet, id = sheet + quality, quality = quality, stack = stack)

    @Test
    fun `une matière première est reconnue à sa fiche`() {
        assertEquals(Family.RAW_HARVESTED, familyOf(item("m0117dxajd01.sitem")))
        assertEquals(Family.SAP_RECHARGE, familyOf(item("item_sap_recharge.sitem")))
        assertEquals(Family.JOB_ITEM, familyOf(item("rpjobitem_201_a0.sitem")))
        assertEquals(Family.TELEPORT, familyOf(item("tp_kami_zora.sitem")))
        assertEquals(Family.OTHER, familyOf(item("bidule.sitem")))
    }

    @Test
    fun `les qualités d'une même matière portent la même clé`() {
        assertEquals(materialKey(item("m0117dxajd01.sitem")),
                     materialKey(item("m0117dxafe01.sitem")))
    }

    @Test
    fun `le tri par famille réunit les matières, du plus bas au plus haut`() {
        val liste = listOf(
            item("bidule.sitem"),
            item("m0117dxajd01.sitem", quality = 250),
            item("m0101dxajd01.sitem", quality = 100),
            item("m0117dxafe01.sitem", quality = 100),
        )
        val range = sortItems(liste, SortOrder.FAMILY) { it.sheet }
        assertEquals(
            listOf("m0101dxajd01.sitem", "m0117dxafe01.sitem",
                   "m0117dxajd01.sitem", "bidule.sitem"),
            range.map { it.sheet },
        )
    }

    @Test
    fun `les pièces d'une tenue se réunissent et se lisent de la tête aux pieds`() {
        // Fiches et noms relevés sur un personnage : le jeu nomme les six
        // pièces de six façons, et deux tenues s'entremêlaient par leur nom.
        val noms = mapOf(
            "icmahb_3.sitem" to "Bottes Kara Paroks",
            "icmahh_3.sitem" to "Casque Kara Parok",
            "icmahv_3.sitem" to "Gilet Kara Parok",
            "icmalb_3.sitem" to "Bottes Kara Wivas",
            "icmalv_3.sitem" to "Gilet Kara Wiva",
        )
        val liste = noms.keys.map { item(it, quality = 250) }.shuffled()
        val range = sortItems(liste, SortOrder.FAMILY) { noms.getValue(it.sheet) }
        assertEquals(
            listOf("Casque Kara Parok", "Gilet Kara Parok", "Bottes Kara Paroks",
                   "Gilet Kara Wiva", "Bottes Kara Wivas"),
            range.map { noms.getValue(it.sheet) },
        )
    }

    @Test
    fun `les bijoux d'une même parure restent ensemble malgré la casse`() {
        // Le jeu écrit « Bague zoraï » avec une capitale et « bracelet zoraï »
        // sans : l'ordre des codes de caractères les séparait de toute la
        // liste, les minuscules venant après le Z.
        val noms = mapOf(
            "iczjb.sitem" to "bracelet zoraï",
            "iczjr.sitem" to "Bague zoraï",
            "iczjd.sitem" to "diadème zoraï",
        )
        val liste = noms.keys.map { item(it, quality = 210) }
        val range = sortItems(liste, SortOrder.FAMILY) { noms.getValue(it.sheet) }
        assertEquals(listOf("diadème zoraï", "Bague zoraï", "bracelet zoraï"),
                     range.map { noms.getValue(it.sheet) })
    }

    @Test
    fun `le tri par nom range comme un dictionnaire, accents compris`() {
        val noms = mapOf("a.sitem" to "Épée Zo'Kovan",
                         "b.sitem" to "Pique",
                         "c.sitem" to "bracelet zoraï")
        val range = sortItems(noms.keys.map { item(it) }, SortOrder.NAME) {
            noms.getValue(it.sheet)
        }
        assertEquals(listOf("bracelet zoraï", "Épée Zo'Kovan", "Pique"),
                     range.map { noms.getValue(it.sheet) })
    }

    @Test
    fun `les armes ne s'intercalent pas entre deux parures`() {
        // Le nom d'une arme se comparait à un code de fiche : la Pique tombait
        // au milieu des bijoux zoraï. Les ensembles d'abord, le reste ensuite.
        val noms = mapOf(
            "iccm2pp.sitem" to "Pique",
            "icfm1bs_3.sitem" to "Bâton Talusyx",
            "icmahb_3.sitem" to "Bottes Kara Paroks",
            "iczja.sitem" to "Anneau de cheville zoraï",
        )
        val range = sortItems(noms.keys.map { item(it, quality = 250) },
                              SortOrder.FAMILY) { noms.getValue(it.sheet) }
        assertEquals(
            listOf("Bottes Kara Paroks", "Anneau de cheville zoraï",
                   "Bâton Talusyx", "Pique"),
            range.map { noms.getValue(it.sheet) },
        )
    }

    @Test
    fun `une arme n'est pas prise pour une pièce de tenue`() {
        assertEquals(null, outfitKey(item("iccm2pp.sitem")))
        assertEquals(null, outfitKey(item("icokamm2ss_2.sitem")))
        assertEquals("icmah_3", outfitKey(item("icmahb_3.sitem")))
        assertEquals("iczj", outfitKey(item("iczja.sitem")))
    }

    @Test
    fun `le tri par quantité met les grosses piles devant`() {
        val liste = listOf(item("a.sitem", stack = 2), item("b.sitem", stack = 40))
        assertEquals(listOf("b.sitem", "a.sitem"),
                     sortItems(liste, SortOrder.QUANTITY) { it.sheet }.map { it.sheet })
    }
}
