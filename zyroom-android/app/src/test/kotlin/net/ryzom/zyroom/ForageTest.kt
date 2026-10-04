package net.ryzom.zyroom

import net.ryzom.zyroom.model.Forage
import net.ryzom.zyroom.model.RELEVE_A_CONFIRMER
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * `Forage` doit dire exactement ce que dit ZyRoom-GTK : les trois cas
 * attendus ci-dessous sont la sortie de `meteo.sorties_de`, relevée sur la
 * même table le 4 octobre 2026.
 */
class ForageTest {

    @Test
    fun `printemps aux Sources Interdites par bon temps`() {
        assertEquals(
            listOf(
                Forage.SUPREME to mapOf(
                    "Carapace" to listOf("Splinter"),
                    "Graines" to listOf("Saurona"),
                ),
                Forage.EXCELLENTE to mapOf(
                    "Boucles" to listOf("Scrath"),
                    "Carapace" to listOf("Horny"),
                    "Fibres" to listOf("Anete"),
                    "Résine" to listOf("Dung"),
                    "Sève" to listOf("Visc"),
                    "Écorce" to listOf("Beckers", "Perfling"),
                ),
            ),
            Forage.sortiesDe(0, "Sources Interdites", "good"),
        )
    }

    @Test
    fun `automne a la Cite Engloutie par temps execrable`() {
        val sorties = Forage.sortiesDe(2, "Cité Engloutie", "worst")
        assertEquals(listOf(Forage.SUPREME, Forage.EXCELLENTE), sorties.map { it.first })
        assertEquals(
            listOf("Anete", "Buo", "Dzao", "Shu"),
            sorties[0].second["Fibres"],
        )
        assertEquals(mapOf("Ambres" to listOf("Zun")), sorties[1].second)
    }

    @Test
    fun `hiver en Terre de la Continuite par mauvais temps`() {
        assertEquals(
            listOf(
                Forage.SUPREME to mapOf(
                    "Carapace" to listOf("Cuty"),
                    "Résine" to listOf("Dung"),
                ),
                Forage.EXCELLENTE to mapOf(
                    "Ambres" to listOf("Sha"),
                    "Bois" to listOf("Motega"),
                    "Carapace" to listOf("Big"),
                    "Huile" to listOf("Koorin", "Pilan"),
                    "Résine" to listOf("Moon"),
                    "Sève" to listOf("Dante", "Enola", "Visc"),
                ),
            ),
            Forage.sortiesDe(3, "Terre de la Continuité", "bad"),
        )
    }

    /** Une croix orange ne se montre que dans la variante dev. */
    @Test
    fun `les croix oranges restent cachees aux joueurs`() {
        val (zone, famille, matiere, saison, condition) = RELEVE_A_CONFIRMER.first().split("|")
        val indice = listOf("PRINTEMPS", "ETE", "AUTOMNE", "HIVER").indexOf(saison)
        val joueurs = Forage.sortiesDe(indice, zone, condition)
        assertTrue(joueurs.none { (_, groupes) -> matiere in groupes[famille].orEmpty() })
        val dev = Forage.sortiesDe(indice, zone, condition, voirAVerifier = true)
        assertTrue(dev.any { (q, groupes) ->
            q == Forage.A_CONFIRMER && matiere in groupes[famille].orEmpty()
        })
    }

    @Test
    fun `une saison inconnue ne sort rien`() {
        assertTrue(Forage.sortiesDe(-1, "Sources Interdites", "good").isEmpty())
    }
}
