package net.ryzom.zyroom

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
