package net.ryzom.zyroom

import kotlinx.coroutines.runBlocking
import net.ryzom.zyroom.data.RosterStore
import net.ryzom.zyroom.model.Member
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/**
 * Le registre du personnel : ce qu'il journalise, et ce qu'il reprend.
 *
 * La reprise verse au journal des mouvements qu'un autre portage a constatés
 * avant que celui-ci ne tienne un registre. Elle ne doit se faire qu'une fois :
 * une ligne effacée ne doit pas revenir au relevé suivant.
 */
class RosterStoreTest {

    @get:Rule
    val dossier = TemporaryFolder()

    private val LUNE = "105906237"

    private fun effectif(vararg gens: Pair<String, String>) =
        gens.map { (nom, grade) -> Member(nom, grade) }

    @Test
    fun `la reprise verse les mouvements de l'autre journal`() = runBlocking {
        val dir = dossier.newFolder()
        RosterStore(dir).record(LUNE, effectif("Paty" to "Officer"))
        val journal = RosterStore(dir).history(LUNE)
        assertEquals(listOf("Paty", "Thysela"), journal.map { it.member }.sorted())
        assertTrue(journal.all { it.kind == "grade" })
        assertTrue(journal.first { it.member == "Thysela" }.promotion)
    }

    /** Sans témoin, chaque relevé rejouerait la reprise : deux, puis quatre… */
    @Test
    fun `la reprise ne se fait qu'une fois`() = runBlocking {
        val dir = dossier.newFolder()
        val magasin = RosterStore(dir)
        repeat(3) { magasin.record(LUNE, effectif("Paty" to "Officer")) }
        assertEquals(2, magasin.history(LUNE).size)
    }

    /** Effacé à dessein, le journal reste effacé. */
    @Test
    fun `une ligne effacée ne revient pas`() = runBlocking {
        val dir = dossier.newFolder()
        val magasin = RosterStore(dir)
        magasin.record(LUNE, effectif("Paty" to "Officer"))
        magasin.clear(LUNE)
        magasin.record(LUNE, effectif("Paty" to "Officer"))
        assertEquals(emptyList<String>(), magasin.history(LUNE).map { it.member })
    }

    /** Une guilde qui n'a rien à reprendre part d'un journal vide. */
    @Test
    fun `les autres guildes ne reprennent rien`() = runBlocking {
        val magasin = RosterStore(dossier.newFolder())
        magasin.record("689325", effectif("Xiom" to "HighOfficer"))
        assertEquals(emptyList<String>(), magasin.history("689325").map { it.member })
    }

    @Test
    fun `le premier relevé ne journalise aucune arrivée`() = runBlocking {
        val magasin = RosterStore(dossier.newFolder())
        val vus = magasin.record("42", effectif("Xiom" to "Leader", "Koii" to "Member"))
        assertEquals(emptyList<String>(), vus.map { it.member })
    }

    @Test
    fun `le relevé suivant voit l'arrivée, le départ et la montée`() = runBlocking {
        val magasin = RosterStore(dossier.newFolder())
        magasin.record("42", effectif("Xiom" to "Officer", "Koii" to "Member"))
        val vus = magasin.record("42", effectif("Xiom" to "HighOfficer", "Paret" to "Member"))
        assertEquals(
            listOf("Koii" to "depart", "Paret" to "arrivee", "Xiom" to "grade"),
            vus.map { it.member to it.kind }.sortedBy { it.first },
        )
    }

    /** Un flux tronqué ne doit pas faire démissionner la guilde entière. */
    @Test
    fun `un relevé vide n'est jamais comparé`() = runBlocking {
        val magasin = RosterStore(dossier.newFolder())
        magasin.record("42", effectif("Xiom" to "Leader"))
        assertEquals(emptyList<String>(), magasin.record("42", emptyList()).map { it.member })
        assertEquals(emptyList<String>(), magasin.history("42").map { it.member })
    }

    /** Ce qu'on ne sait pas lire, on le garde : un journal n'est pas remplaçable. */
    @Test
    fun `l'élagage recopie les lignes illisibles`() = runBlocking {
        val dir = dossier.newFolder()
        val magasin = RosterStore(dir)
        val vieux = System.currentTimeMillis() / 1000 - 40 * 86400
        File(dir, "roster-42.jsonl").writeText(
            """{"at":$vieux,"member":"Vieux","kind":"depart","from":"Member"}""" + "\n" +
                "ceci n'est pas du json\n"
        )
        magasin.record("42", effectif("Xiom" to "Leader"))
        magasin.record("42", effectif("Xiom" to "Leader", "Koii" to "Member"))
        val restant = File(dir, "roster-42.jsonl").readLines().filter { it.isNotBlank() }
        assertTrue("ceci n'est pas du json" in restant)
        assertTrue(restant.none { "Vieux" in it })
    }
}
