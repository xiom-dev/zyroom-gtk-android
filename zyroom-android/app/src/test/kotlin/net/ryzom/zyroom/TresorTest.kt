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

/**
 * Le trésor au journal : les dappers qui entrent et qui sortent.
 *
 * Miroir de `tests/test_argent.py` côté GTK. L'API rend l'argent à part des
 * coffres (`<money>`), et l'application ne l'affichait qu'en haut de l'écran —
 * un nombre du jour, sans mémoire. Il suit maintenant le même chemin que les
 * objets : l'instantané le porte sous une clé réservée, la comparaison de deux
 * instantanés en tire un mouvement.
 *
 * Le cas qui a dicté le reste est la toute première relève après la mise à
 * jour : l'instantané précédent, écrit par l'ancienne version, ne connaît pas
 * l'argent. Sans garde, le journal s'ouvrirait sur une entrée de
 * soixante-dix-neuf millions de dappers qui n'a jamais eu lieu.
 */
class TresorTest {

    @get:Rule
    val dossier = TemporaryFolder()

    private val suivie = EntityStore.Suivie("105906237", Entity.Kind.GUILD, "clef")

    private fun guilde(argent: Long, quantite: Int = 10) = Entity(
        kind = Entity.Kind.GUILD,
        id = "105906237",
        name = "La Lune Eternelle",
        dappers = argent,
        inventories = listOf(Inventory(
            key = "c1", label = "Coffre 1",
            items = listOf(Item(sheet = "mp.sitem", id = "mp",
                                quality = 200, stack = quantite)))),
    )

    private fun store() = MovementStore(dossier.newFolder())

    // ------------------------------------------------------------ mouvements

    @Test
    fun `ce qui entre dans le trésor`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(79_000_000))
        val mouvement = magasin.record(suivie, guilde(80_200_000)).single()

        assertEquals(MovementStore.MONEY_KEY, mouvement.invKey)
        assertEquals(1_200_000L, mouvement.delta)
        assertEquals(79_000_000L, mouvement.before)
        assertEquals(80_200_000L, mouvement.after)
    }

    @Test
    fun `ce qui en sort`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(80_200_000))
        assertEquals(-1_200_000L, magasin.record(suivie, guilde(79_000_000))
            .single().delta)
    }

    @Test
    fun `un trésor qui ne bouge pas ne dit rien`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(79_000_000))
        assertEquals(emptyList<MovementStore.Movement>(),
                     magasin.record(suivie, guilde(79_000_000)))
    }

    @Test
    fun `la première relève ne journalise pas le magot`() = runBlocking {
        // Sans état antérieur, le trésor entier passerait pour une entrée.
        assertEquals(emptyList<MovementStore.Movement>(),
                     store().record(suivie, guilde(79_000_000)))
    }

    @Test
    fun `un instantané qui ignorait l'argent reste muet une fois`() = runBlocking {
        // Ce qu'écrivait la version précédente : des coffres, pas de trésor.
        val magasin = store()
        magasin.record(suivie, guilde(argent = 0))          // API muette
        assertEquals(emptyList<MovementStore.Movement>(),
                     magasin.record(suivie, guilde(79_000_000)))
        // …et la relève d'après dit la vérité.
        assertEquals(1_000_000L,
                     magasin.record(suivie, guilde(80_000_000)).single().delta)
    }

    @Test
    fun `le trésor passe devant les objets`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(79_000_000, quantite = 10))
        val mouvements = magasin.record(suivie, guilde(80_000_000, quantite = 15))

        assertEquals(2, mouvements.size)
        assertEquals(MovementStore.MONEY_KEY, mouvements[0].invKey)
        assertEquals("c1", mouvements[1].invKey)
    }

    @Test
    fun `les millions ne débordent pas`() = runBlocking {
        // Au-delà de ce qu'un Int retient : c'est la raison du passage en Long.
        val magasin = store()
        magasin.record(suivie, guilde(3_000_000_000L))
        assertEquals(1_000_000_000L,
                     magasin.record(suivie, guilde(4_000_000_000L)).single().delta)
    }

    // -------------------------------------------------------------- écriture

    @Test
    fun `le journal relu garde le trésor`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(79_000_000))
        magasin.record(suivie, guilde(80_200_000))

        val relu = magasin.history(suivie).single()
        assertEquals(MovementStore.MONEY_KEY, relu.invKey)
        assertEquals(1_200_000L, relu.delta)
        assertEquals(MovementStore.MONEY_SHEET, relu.sheet)
    }

    // ------------------------------------------------------------ lisibilité

    @Test
    fun `les milliers sont espacés`() {
        assertEquals("79 000 000", MovementStore.montant(79_000_000))
        assertEquals("1 200 000", MovementStore.montant(1_200_000))
        assertEquals("999", MovementStore.montant(999))
        assertEquals("0", MovementStore.montant(0))
        assertEquals("-1 200 000", MovementStore.montant(-1_200_000))
    }

    @Test
    fun `la ligne rédigée se lit`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(79_000_000))
        val ligne = MovementStore.describe(
            magasin.record(suivie, guilde(80_200_000)).single()) { it }

        assertTrue(ligne, "1 200 000 dappers entrés" in ligne)
        assertTrue(ligne, "79 000 000 > 80 200 000" in ligne)
    }

    @Test
    fun `une sortie se dit sortie`() = runBlocking {
        val magasin = store()
        magasin.record(suivie, guilde(80_200_000))
        val ligne = MovementStore.describe(
            magasin.record(suivie, guilde(79_000_000)).single()) { it }

        assertTrue(ligne, "1 200 000 dappers sortis" in ligne)
    }
}
