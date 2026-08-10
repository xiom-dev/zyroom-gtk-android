package net.ryzom.zyroom

import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * La variante du mainteneur montre tout — c'est à cela qu'elle sert.
 *
 * Le pendant de `MasqueGuildeTest` : si les deux fichiers de
 * `src/<variante>/kotlin/` étaient intervertis, l'un des deux jeux de tests
 * échouerait, quel que soit le sens de l'erreur.
 */
class MasqueDevTest {

    @Test
    fun `la variante dev ne masque rien`() {
        assertFalse("la variante du mainteneur doit tout montrer", MASQUE_COFFRES)
    }
}
