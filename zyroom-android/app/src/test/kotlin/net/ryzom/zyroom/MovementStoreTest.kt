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
import org.junit.Test
import org.junit.rules.TemporaryFolder

/** Le journal des mouvements, porté de `movements.py`. */
class MovementStoreTest {

    @get:Rule
    val dossier = TemporaryFolder()

    private val suivie = EntityStore.Suivie("105906237", Entity.Kind.GUILD, "clef")

    private fun guilde(vararg contenu: Pair<String, List<Item>>) = Entity(
        kind = Entity.Kind.GUILD,
        id = "105906237",
        name = "La Lune Eternelle",
        inventories = contenu.map { (cle, items) ->
            Inventory(key = cle, label = "Coffre $cle", items = items)
        },
    )

    private fun item(sheet: String, quality: Int, stack: Int) =
        Item(sheet = sheet, id = "$sheet$quality", quality = quality, stack = stack)

    private fun store() = MovementStore(dossier.newFolder())

    @Test
    fun `le premier relevé ne journalise rien`() = runBlocking {
        val magasin = store()
        val mouvements = magasin.record(
            suivie, guilde("c1" to listOf(item("mp_hard.sitem", 200, 999))))
        // Sans état antérieur, tout l'inventaire passerait pour un arrivage.
        assertEquals(emptyList<MovementStore.Movement>(), mouvements)
        assertEquals(emptyList<MovementStore.Movement>(), magasin.history(suivie))
    }

    @Test
    fun `ajout, retrait et changement de quantité sont distingués`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde("c1" to listOf(
            item("mp_hard.sitem", 200, 999),
            item("cuir.sitem", 220, 50),
        )))

        val mouvements = magasin.record(suivie, guilde("c1" to listOf(
            item("mp_hard.sitem", 200, 499),      // quantité changée
            item("croc.sitem", 250, 167),         // apparu
            // cuir.sitem a disparu
        )))

        assertEquals(3, mouvements.size)
        val parFiche = mouvements.associateBy { it.sheet }

        assertEquals(MovementStore.Kind.MODIFIED, parFiche["mp_hard.sitem"]!!.kind)
        assertEquals(-500L, parFiche["mp_hard.sitem"]!!.delta)
        assertEquals(999L, parFiche["mp_hard.sitem"]!!.before)
        assertEquals(499L, parFiche["mp_hard.sitem"]!!.after)

        assertEquals(MovementStore.Kind.ADDED, parFiche["croc.sitem"]!!.kind)
        assertEquals(167L, parFiche["croc.sitem"]!!.delta)
        assertEquals(250, parFiche["croc.sitem"]!!.quality)

        assertEquals(MovementStore.Kind.REMOVED, parFiche["cuir.sitem"]!!.kind)
        assertEquals(-50L, parFiche["cuir.sitem"]!!.delta)
    }

    @Test
    fun `un état inchangé ne produit aucun mouvement`() = runBlocking {
        val magasin = store()
        val etat = guilde("c1" to listOf(item("mp_hard.sitem", 200, 999)))
        magasin.record(suivie, etat)
        // L'API resert le même document tant que cached_until n'est pas dépassé :
        // relire ne doit rien inscrire.
        assertEquals(emptyList<MovementStore.Movement>(), magasin.record(suivie, etat))
    }

    @Test
    fun `un contenant disparu ne compte pas comme un retrait`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(
            "c1" to listOf(item("mp_hard.sitem", 200, 999)),
            "c2" to listOf(item("cuir.sitem", 220, 50)),
        ))
        // c2 n'est plus servi — coffre masqué, bête vendue. Son contenu ne doit
        // pas être journalisé comme sorti.
        val mouvements = magasin.record(suivie, guilde(
            "c1" to listOf(item("mp_hard.sitem", 200, 999))))
        assertEquals(emptyList<MovementStore.Movement>(), mouvements)
    }

    /**
     * Le cas qui compte : on a d'abord relevé le coffre garni (variante dev, ou
     * version antérieure au masquage), puis il devient masqué. Sans exclusion,
     * la comparaison verrait un retrait par objet et recopierait dans le journal
     * la liste même qu'on cherche à cacher.
     */
    @Test
    fun `un coffre masqué ne fuit pas dans le journal`() = runBlocking {
        val magasin = store()
        val garni = Entity(
            kind = Entity.Kind.GUILD, id = "105906237", name = "La Lune Eternelle",
            inventories = listOf(Inventory("c1", "Coffre 1",
                listOf(item("secret_a.sitem", 250, 99), item("secret_b.sitem", 250, 42)))))
        magasin.record(suivie, garni)

        val masque = Entity(
            kind = Entity.Kind.GUILD, id = "105906237", name = "La Lune Eternelle",
            inventories = listOf(Inventory("c1", "Coffre 1", emptyList(), masked = true)))
        val mouvements = magasin.record(suivie, masque)

        assertEquals(emptyList<MovementStore.Movement>(), mouvements)
        val journal = magasin.history(suivie)
        assertTrue("aucune fiche du coffre masqué ne doit apparaître",
                   journal.none { "secret" in it.sheet })
    }

    @Test
    fun `le journal ressort du plus récent au plus ancien`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde("c1" to listOf(item("a.sitem", 100, 10))))
        magasin.record(suivie, guilde("c1" to listOf(item("a.sitem", 100, 20))))  // +10
        Thread.sleep(1100)   // l'horodatage est à la seconde
        magasin.record(suivie, guilde("c1" to listOf(item("a.sitem", 100, 5))))   // -15

        val histoire = magasin.history(suivie)
        assertEquals(2, histoire.size)
        assertEquals(-15L, histoire[0].delta)
        assertEquals(10L, histoire[1].delta)
        assertTrue(histoire[0].at >= histoire[1].at)
    }

    @Test
    fun `vider efface le journal`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde("c1" to listOf(item("a.sitem", 100, 10))))
        magasin.record(suivie, guilde("c1" to listOf(item("a.sitem", 100, 20))))
        assertEquals(1, magasin.history(suivie).size)

        magasin.clear(suivie)
        assertEquals(emptyList<MovementStore.Movement>(), magasin.history(suivie))
    }

    @Test
    fun `la ligne rédigée reprend la formulation de l'original`() {
        val ajout = MovementStore.Movement(
            at = 0, invKey = "c1", invLabel = "Coffre 1", sheet = "croc.sitem",
            quality = 250, kind = MovementStore.Kind.ADDED, delta = 167,
            before = 0, after = 167)
        assertEquals("l'objet Croc Q250 a été ajouté (167)",
                     MovementStore.describe(ajout) { "Croc" })

        val retrait = ajout.copy(kind = MovementStore.Kind.REMOVED, delta = -167,
                                 before = 167, after = 0)
        assertEquals("l'objet Croc Q250 a été retiré (167)",
                     MovementStore.describe(retrait) { "Croc" })

        val change = ajout.copy(kind = MovementStore.Kind.MODIFIED, delta = -500,
                                before = 999, after = 499)
        assertEquals("la quantité de l'objet Croc Q250 a changé (999 > 499)",
                     MovementStore.describe(change) { "Croc" })
    }
}
