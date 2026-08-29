package net.ryzom.zyroom

import kotlinx.coroutines.runBlocking
import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.Item
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Rule
import net.ryzom.zyroom.data.volumeAlerts
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * La date d'un mouvement : celle du relevé, pas celle de la relève.
 *
 * Le journal datait chaque mouvement de l'horloge du téléphone au moment où
 * l'application interrogeait l'API. Relever tous les soirs vers la même heure
 * donnait donc un journal où chaque jour portait la même heure, et trois jours
 * d'absence s'écrasaient sur l'instant du retour.
 *
 * L'API ne recalcule pas un flux à la demande : elle sert le dernier qu'elle
 * ait mis en cache, et l'inscrit dans la balise racine — `created`, à côté du
 * `cached_until` dont [Entity.isStale] se sert déjà. Le parseur le lisait
 * depuis toujours ; le journal, lui, l'ignorait.
 *
 * Ce qu'aucun de ces tests ne prétend, c'est que ce soit l'heure du mouvement :
 * l'API rend un état, jamais un historique. On sait seulement qu'un mouvement a
 * eu lieu entre deux relevés, et la date du relevé est la meilleure borne que
 * le flux fournisse.
 */
class HorodatageTest {

    @get:Rule
    val dossier = TemporaryFolder()

    private val suivie = EntityStore.Suivie("105906237", Entity.Kind.GUILD, "clef")

    private fun guilde(created: Long, stack: Int) = Entity(
        kind = Entity.Kind.GUILD,
        id = "105906237",
        name = "La Lune Eternelle",
        created = created,
        inventories = listOf(Inventory(
            key = "c1",
            label = "Coffre 1",
            items = listOf(Item(sheet = "mp.sitem", id = "mp", quality = 250, stack = stack)),
        )),
    )

    private fun maintenant() = System.currentTimeMillis() / 1000

    // ------------------------------------------------------------ dateReleve

    @Test
    fun `la date du flux est retenue`() {
        assertEquals(RELEVE, MovementStore.dateReleve(guilde(RELEVE, 1)))
    }

    @Test
    fun `sans date on retombe sur l'horloge`() {
        // Un flux d'avant cet attribut, ou tronqué : mieux vaut approximatif.
        val quand = MovementStore.dateReleve(guilde(0, 1))
        assertTrue(kotlin.math.abs(quand - maintenant()) <= 5)
    }

    @Test
    fun `une date venue de l'avenir est écartée`() {
        // Elle trahit une horloge de téléphone en retard, pas un flux de
        // demain. La laisser passer mettrait la ligne en tête du journal.
        val quand = MovementStore.dateReleve(guilde(maintenant() + 86_400, 1))
        assertTrue(kotlin.math.abs(quand - maintenant()) <= 5)
    }

    @Test
    fun `une date d'avant l'ouverture du jeu est écartée`() {
        val quand = MovementStore.dateReleve(guilde(42, 1))
        assertTrue(kotlin.math.abs(quand - maintenant()) <= 5)
    }

    @Test
    fun `une heure de décalage reste tolérée`() {
        // Les horloges ne sont jamais tout à fait d'accord ; une heure absorbe
        // le désaccord sans laisser passer une date folle.
        val presque = maintenant() + 600
        assertEquals(presque, MovementStore.dateReleve(guilde(presque, 1)))
    }

    // ------------------------------------------------------ bout en bout

    @Test
    fun `le journal porte la date du relevé`() = runBlocking {
        val magasin = MovementStore(dossier.newFolder())
        magasin.record(suivie, guilde(RELEVE_PRECEDENT, 10))
        val mouvements = magasin.record(suivie, guilde(RELEVE, 22))

        assertEquals(1, mouvements.size)
        assertEquals(RELEVE, mouvements.first().at)
        // Et la date survit à l'écriture en JSON Lines puis à la relecture.
        assertEquals(listOf(RELEVE), magasin.history(suivie).map { it.at })
    }

    // ------------------------------------------------- libellés de coffres

    /**
     * Relevés tels quels dans le journal de la guilde : l'API tronque le nom
     * d'un coffre à une quarantaine de signes, si bien que la parenthèse ne se
     * referme presque jamais.
     */
    @Test
    fun `le parenthétique disparaît`() {
        val releves = listOf(
            "Coffre 15 — La Lune Des Maraudeurs(Gh Armure" to "Coffre 15 — La Lune Des Maraudeurs",
            "Coffre 2 — La Resserre Lunaire 1/2 (Equipem" to "Coffre 2 — La Resserre Lunaire 1/2",
            "Coffre 9 — La Lune d'Ambre(Craft Bijoux/Amp" to "Coffre 9 — La Lune d'Ambre",
        )
        releves.forEach { (brut, attendu) ->
            assertEquals(attendu, MovementStore.sansParenthese(brut))
        }
    }

    @Test
    fun `ce qui n'en a pas ne bouge pas`() {
        listOf("Sac", "Coffre 1", "Appartement", "Trésor", "Zig 3").forEach {
            assertEquals(it, MovementStore.sansParenthese(it))
        }
    }

    @Test
    fun `un libellé entièrement parenthésé est gardé`() {
        // Mieux vaut un libellé étrange qu'une colonne muette.
        assertEquals("(Gh Armure", MovementStore.sansParenthese("(Gh Armure"))
        assertEquals("", MovementStore.sansParenthese(""))
    }

    private companion object {
        /** Le relevé du 22 août 2026 à 00h09, tel que l'API l'a horodaté. */
        const val RELEVE = 1_787_350_189L

        /** Celui de la veille au soir, qui lui sert de terme de comparaison. */
        const val RELEVE_PRECEDENT = 1_787_263_789L
    }

    @Test
    fun `l'alerte de volume coupe comme le journal`() {
        // La cloche nommait le coffre en entier, phrase pendante comprise :
        // le journal coupait depuis toujours, l'alerte non.
        val coffre = Inventory(
            key = "chest15",
            label = "Coffre 15 — La Lune Des Maraudeurs(Gh Armure",
            items = listOf(Item(sheet = "m0001dxadf01.sitem", stack = 9600,
                                volume = 4800.0)),
            capacity = 5000,
        )
        val entite = Entity(kind = Entity.Kind.GUILD, id = "1",
                            name = "La Lune Eternelle",
                            inventories = listOf(coffre))
        val alertes = volumeAlerts(entite, 90)
        assertEquals(1, alertes.size)
        assertEquals("Coffre 15 — La Lune Des Maraudeurs : 96 % plein",
                     alertes.first().title)
    }
}
