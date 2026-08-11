package net.ryzom.zyroom

import net.ryzom.zyroom.model.NIVEAUX_AVANT_POSTES
import net.ryzom.zyroom.model.NOMS_AVANT_POSTES
import net.ryzom.zyroom.names.NameDb
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * Le recours quand le pack du client n'est pas là.
 *
 * La variante F-Droid ne peut pas l'embarquer — sa licence n'est pas établie —
 * et affichait « fyros_outpost_04 » là où il faut lire « Ferme de Malmontagne ».
 */
class OutpostNamesTest {

    @Test
    fun `un avant-poste se nomme sans le pack`() {
        assertEquals("Ferme de Malmontagne",
                     NameDb.EMPTY.nameOf("fyros_outpost_04.outpost"))
    }

    /**
     * C'est la source du jeu : elle suit ses mises à jour, pas nous.
     *
     * Le pack se lit par `parse`, le constructeur étant privé : on en
     * fabrique donc un minuscule, d'un seul enregistrement, plutôt que
     * d'ouvrir la classe pour l'essai.
     */
    @Test
    fun `le pack reste prioritaire`() {
        val db = NameDb.parse(paquet("fyros_outpost_04.outpost", "Nom venu du pack"))
        assertEquals("Nom venu du pack", db.nameOf("fyros_outpost_04.outpost"))
    }

    /**
     * Un pack d'un seul nom, au format du jeu : clé, séparateur, valeur.
     *
     * La longueur de la valeur se compte en **caractères**, pas en octets : le
     * séparateur 1 annonce de l'UTF-16, deux octets par caractère. En y
     * mettant des octets, l'enregistrement était rejeté et l'essai passait
     * pour concluant alors qu'il mesurait le recours.
     */
    private fun paquet(cle: String, valeur: String): ByteArray {
        val k = cle.toByteArray(Charsets.UTF_8)
        val v = valeur.toByteArray(Charsets.UTF_16LE)
        return java.nio.ByteBuffer.allocate(4 + k.size + 1 + 4 + v.size)
            .order(java.nio.ByteOrder.LITTLE_ENDIAN)
            .putInt(k.size).put(k).put(1).putInt(valeur.length).put(v).array()
    }

    /**
     * Les quatre avant-postes des Primes sont écartés du relevé : ils portent
     * « ((En test, instable)) » et n'ont jamais été ouverts au jeu.
     */
    @Test
    fun `un avant-poste inconnu rend sa clé`() {
        assertEquals("primes_outpost_01.outpost",
                     NameDb.EMPTY.nameOf("primes_outpost_01.outpost"))
    }

    @Test
    fun `les autres fiches ne sont pas touchées`() {
        assertEquals("bidule.sitem", NameDb.EMPTY.nameOf("bidule.sitem"))
    }

    /** Sinon l'onglet afficherait un code brut pour celui-là. */
    @Test
    fun `chaque avant-poste de notre table a un nom`() {
        NIVEAUX_AVANT_POSTES.keys.forEach { code ->
            val nom = NameDb.EMPTY.nameOf("$code.outpost")
            assertFalse(code, "_outpost_" in nom)
        }
    }

    @Test
    fun `le relevé écarte les avant-postes instables`() {
        assertFalse("primes_outpost_01" in NOMS_AVANT_POSTES)
    }
}
