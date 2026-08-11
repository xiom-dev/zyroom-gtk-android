package net.ryzom.zyroom

import org.junit.Assert.assertTrue
import net.ryzom.zyroom.ui.SYMBOLES_EMBARQUES
import net.ryzom.zyroom.ui.symboleDe
import org.junit.Assert.assertNotNull
import org.junit.Test

/**
 * La variante distribuée masque le petit coffre. C'est sa raison d'être.
 *
 * Les autres tests comparent le réglage à ce que fait l'analyseur : ils
 * passeraient tout aussi bien si la variante guilde était compilée avec
 * `MASQUE_COFFRES = false`, l'un et l'autre étant alors faux ensemble. Celui-ci
 * fixe la valeur elle-même, et il ne vit que dans le jeu de tests de la
 * variante guilde — inverser les deux fichiers de `src/<variante>/kotlin/`
 * ferait donc échouer la livraison au lieu de la faire partir masque baissé.
 */
class MasqueGuildeTest {

    @Test
    fun `la variante guilde masque les coffres`() {
        assertTrue("la variante distribuée doit masquer le petit coffre",
                   MASQUE_COFFRES)
    }

    @Test
    fun `la variante guilde se met à jour elle-même`() {
        // Elle n'a pas de logithèque pour le faire : sans cela, les joueurs
        // resteraient sur la version du jour de leur installation.
        assertTrue(MISES_A_JOUR_INTEGREES)
    }

    /**
     * Les variantes qu'on distribue soi-même embarquent les symboles.
     *
     * Ils vivent dans `src/packRes`, un répertoire que seules ces variantes
     * déclarent : oublier la déclaration les ferait disparaître sans rien
     * casser à la compilation.
     */
    @Test
    fun `guilde embarque les symboles de matière`() {
        assertTrue("les symboles doivent être dans la variante guilde",
                   SYMBOLES_EMBARQUES)
        assertNotNull("« Sève » a un symbole", symboleDe("Sève"))
    }
}
