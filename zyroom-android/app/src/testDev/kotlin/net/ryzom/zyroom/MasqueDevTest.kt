package net.ryzom.zyroom

import org.junit.Assert.assertFalse
import net.ryzom.zyroom.ui.SYMBOLES_EMBARQUES
import net.ryzom.zyroom.ui.symboleDe
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
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

    /**
     * Les variantes qu'on distribue soi-même embarquent les symboles.
     *
     * Ils vivent dans `src/packRes`, un répertoire que seules ces variantes
     * déclarent : oublier la déclaration les ferait disparaître sans rien
     * casser à la compilation.
     */
    @Test
    fun `dev embarque les symboles de matière`() {
        assertTrue("les symboles doivent être dans la variante dev",
                   SYMBOLES_EMBARQUES)
        assertNotNull("« Sève » a un symbole", symboleDe("Sève"))
    }
}
