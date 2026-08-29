package net.ryzom.zyroom

import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.MovementStore.Movement
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/**
 * Deux journaux qui se racontent ce que l'autre a vu.
 *
 * L'API de Ryzom ne rend qu'un état, jamais un historique : un mouvement se
 * déduit de deux relevés successifs, et chaque application ne connaît donc que
 * ce qu'elle a regardé elle-même.
 *
 * Le cas qui a motivé ce fichier est réel, relevé le 29 août 2026 sur le
 * trésor de La Lune Éternelle : le bureau avait vu deux mouvements, le
 * téléphone un seul, et c'était le même argent.
 */
class FusionTest {

    private fun mv(
        at: Long, before: Long, after: Long,
        inv: String = "money", sheet: String = "dappers", q: Int = 0,
    ) = Movement(at, inv, "", sheet, q, MovementStore.Kind.MODIFIED,
                 after - before, before, after)

    @Test
    fun `le gros ecart du telephone cede au detail du bureau`() {
        val bureau = listOf(
            mv(1787000000, 75000000, 75440000),      // 24/08  +440 000
            mv(1787345000, 75440000, 73640000),      // 28/08  -1 800 000
        )
        val telephone = listOf(mv(1788007080, 75000000, 73640000))

        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(bureau, telephone)

        assertEquals(2, fusionne.size)
        assertEquals(0, ajoutes)
        assertEquals(setOf(75000000L to 75440000L, 75440000L to 73640000L),
                     fusionne.map { it.before to it.after }.toSet())
    }

    @Test
    fun `dans l'autre sens le telephone gagne le detail`() {
        val bureau = listOf(
            mv(1787000000, 75000000, 75440000),
            mv(1787345000, 75440000, 73640000),
        )
        val telephone = listOf(mv(1788007080, 75000000, 73640000))

        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(telephone, bureau)

        assertEquals(2, fusionne.size)
        assertEquals(2, ajoutes)
        assertFalse(fusionne.any { it.before == 75000000L && it.after == 73640000L })
    }

    @Test
    fun `un ecart que personne ne detaille est garde`() {
        val bureau = listOf(mv(1787345000, 75440000, 73640000))
        val telephone = listOf(mv(1788007080, 75000000, 73640000))
        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(bureau, telephone)
        assertEquals(2, fusionne.size)
        assertEquals(1, ajoutes)
    }

    @Test
    fun `le meme pas vu des deux cotes ne compte qu'une fois`() {
        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(
            listOf(mv(1787345000, 75440000, 73640000)),
            listOf(mv(1788000000, 75440000, 73640000)))
        assertEquals(1, fusionne.size)
        assertEquals(0, ajoutes)
    }

    @Test
    fun `le plus ancien horodatage l'emporte`() {
        // Il dit quand on a regarde, pas quand la chose est arrivee : le
        // premier a avoir vu date le mieux.
        val (fusionne, _) = MovementStore.Fusion.fusionner(
            listOf(mv(1788007080, 100, 90)), listOf(mv(1787345000, 100, 90)))
        assertEquals(1, fusionne.size)
        assertEquals(1787345000L, fusionne.first().at)
    }

    @Test
    fun `deux objets differents ne se melangent pas`() {
        val a = mv(1787000000, 10, 20, inv = "chest1", sheet = "ambre.sitem")
        val b = mv(1787000000, 10, 20, inv = "chest1", sheet = "resine.sitem")
        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(listOf(a), listOf(b))
        assertEquals(2, fusionne.size)
        assertEquals(1, ajoutes)
    }

    @Test
    fun `un meme objet dans deux coffres reste deux trajets`() {
        val a = mv(1787000000, 10, 20, inv = "chest1", sheet = "ambre.sitem")
        val b = mv(1787000000, 10, 20, inv = "chest2", sheet = "ambre.sitem")
        val (fusionne, _) = MovementStore.Fusion.fusionner(listOf(a), listOf(b))
        assertEquals(2, fusionne.size)
    }

    @Test
    fun `un aller-retour ne fait pas disparaitre les deux pas`() {
        // On vend puis on rachete : le compteur repasse par une valeur connue,
        // et 100 -> 90 -> 100 ne doit rien faire ecarter.
        val journal = listOf(mv(1787000000, 100, 90), mv(1787001000, 90, 100))
        val (fusionne, ajoutes) = MovementStore.Fusion.fusionner(journal, emptyList())
        assertEquals(2, fusionne.size)
        assertEquals(0, ajoutes)
    }

    @Test
    fun `une ligne du bureau se lit ici`() {
        // Le bureau nomme trois champs autrement et ecrit ses `kind` en bas
        // de casse ; son horodatage porte des decimales.
        val store = MovementStore(java.io.File("/inexistant"))
        val venu = store.lireEtranger(JSONObject("""
            {"ts": 1788007080.5, "inv": "money", "label": "Trésor",
             "sheet": "dappers", "q": 0, "kind": "modified",
             "delta": -1360000, "old": 75000000, "new": 73640000}
        """.trimIndent()))
        assertEquals(1788007080L, venu.at)
        assertEquals(75000000L, venu.before)
        assertEquals(73640000L, venu.after)
        assertEquals(MovementStore.Kind.MODIFIED, venu.kind)
    }

    @Test
    fun `une ligne d'ici se relit aussi`() {
        val store = MovementStore(java.io.File("/inexistant"))
        val venu = store.lireEtranger(JSONObject("""
            {"at": 1788007080, "inv": "chest1", "sheet": "ambre.sitem", "q": 150,
             "kind": "ADDED", "delta": 12, "before": 0, "after": 12}
        """.trimIndent()))
        assertEquals(0L, venu.before)
        assertEquals(12L, venu.after)
        assertEquals(MovementStore.Kind.ADDED, venu.kind)
    }
}
