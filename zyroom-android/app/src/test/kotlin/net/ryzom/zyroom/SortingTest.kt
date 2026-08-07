package net.ryzom.zyroom

import net.ryzom.zyroom.model.Family
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.SortOrder
import net.ryzom.zyroom.model.familyOf
import net.ryzom.zyroom.model.materialKey
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
    fun `le tri par quantité met les grosses piles devant`() {
        val liste = listOf(item("a.sitem", stack = 2), item("b.sitem", stack = 40))
        assertEquals(listOf("b.sitem", "a.sitem"),
                     sortItems(liste, SortOrder.QUANTITY) { it.sheet }.map { it.sheet })
    }
}
