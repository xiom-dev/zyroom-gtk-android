package net.ryzom.zyroom

import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.SortOrder
import net.ryzom.zyroom.model.chercheDansTout
import net.ryzom.zyroom.ui.normalise
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** La recherche doit ignorer la casse et les accents, comme la version GTK. */
class SearchTest {

    @Test
    fun `met en minuscules et retire les accents`() {
        assertEquals("legerete", normalise("Légèreté"))
        assertEquals("ambre de choix", normalise("Ambre de Choix"))
    }

    @Test
    fun `une recherche sans accent trouve le mot accentué`() {
        assertTrue(normalise("sève") in normalise("Charge de Sève"))
        assertTrue(normalise("seve") in normalise("Charge de Sève"))
    }

    @Test
    fun `laisse tranquille ce qui n'a pas d'accent`() {
        assertEquals("m0117dxajd01.sitem", normalise("m0117dxajd01.sitem"))
    }
}

/**
 * Chercher, c'est chercher partout.
 *
 * Le champ vide montre le contenant choisi ; dès qu'on tape, les dix-sept
 * coffres d'une guilde sont fouillés d'un coup, et chaque groupe garde le nom
 * du sien — trouver l'objet sans dire où il est ne répondrait pas à la question.
 */
class RechercheDansTousLesCoffresTest {

    private val noms = mapOf(
        "m0117dxajd01.sitem" to "Écorce Beckers",
        "m0101dxajd01.sitem" to "Sève Dante",
        "iczja.sitem" to "Anneau de cheville zoraï",
    )

    private fun item(sheet: String, slot: Int = 0) =
        Item(sheet = sheet, id = "$sheet-$slot", slot = slot, quality = 250)

    private val coffres = listOf(
        Inventory("c1", "Coffre 1", listOf(item("m0117dxajd01.sitem"))),
        Inventory("c2", "Coffre 2", listOf(item("m0101dxajd01.sitem"))),
        Inventory("c3", "Coffre 3", listOf(item("m0117dxajd01.sitem", 1),
                                           item("iczja.sitem"))),
    )

    private fun cherche(quoi: String, choisi: Int = 0) = chercheDansTout(
        inventaires = coffres,
        contenantChoisi = choisi,
        recherche = quoi,
        order = SortOrder.FAMILY,
        nameOf = { noms.getValue(it.sheet) },
        normalise = ::normalise,
    )

    @Test
    fun `sans recherche, seul le contenant choisi`() {
        val vu = cherche("", choisi = 1)
        assertEquals(listOf("Coffre 2"), vu.map { it.first })
        assertEquals(1, vu.first().second.size)
    }

    @Test
    fun `une recherche traverse tous les coffres et dit lesquels`() {
        val vu = cherche("beckers")
        assertEquals(listOf("Coffre 1", "Coffre 3"), vu.map { it.first })
        assertEquals(1, vu[0].second.size)
        assertEquals(1, vu[1].second.size)
    }

    @Test
    fun `les coffres sans réponse disparaissent`() {
        assertEquals(listOf("Coffre 3"), cherche("anneau").map { it.first })
    }

    @Test
    fun `la recherche ignore la casse et les accents`() {
        assertEquals(cherche("Écorce").map { it.first }, cherche("ecorce").map { it.first })
    }

    /** Sans pack chargé il ne reste que la fiche : elle doit rester cherchable. */
    @Test
    fun `chercher une fiche fonctionne aussi`() {
        assertEquals(listOf("Coffre 2"), cherche("m0101").map { it.first })
    }

    @Test
    fun `rien ne correspond, rien n'est rendu`() {
        assertEquals(emptyList<String>(), cherche("bidule").map { it.first })
    }
}
