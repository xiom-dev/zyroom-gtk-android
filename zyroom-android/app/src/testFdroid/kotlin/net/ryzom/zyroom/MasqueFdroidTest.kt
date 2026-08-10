package net.ryzom.zyroom

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * La variante publiée par la logithèque : elle masque, et elle ne se met pas à
 * jour toute seule.
 *
 * Deux règles qu'un remaniement pourrait défaire sans qu'on s'en aperçoive :
 * la première tient au respect des joueurs, la seconde à ce que F-Droid exige
 * pour accepter une application. Les fixer ici les rend visibles à la
 * construction plutôt qu'au refus.
 */
class MasqueFdroidTest {

    @Test
    fun `la variante F-Droid masque les coffres`() {
        assertTrue("une variante publique doit masquer le petit coffre",
                   MASQUE_COFFRES)
    }

    @Test
    fun `la variante F-Droid ne se met pas à jour elle-même`() {
        assertFalse("F-Droid refuse une application qui installe des APK",
                    MISES_A_JOUR_INTEGREES)
    }
}
