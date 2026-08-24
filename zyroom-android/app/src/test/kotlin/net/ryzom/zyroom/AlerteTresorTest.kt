package net.ryzom.zyroom

import net.ryzom.zyroom.data.Alert
import net.ryzom.zyroom.data.MovementStore
import net.ryzom.zyroom.data.WatchStore
import net.ryzom.zyroom.data.moneyAlerts
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.model.Inventory
import net.ryzom.zyroom.model.Item
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

/**
 * La cloche a le droit de parler du trésor, et de lui seul parmi les mouvements.
 *
 * La règle du projet est qu'un mouvement ne sonne pas : ranger douze matières
 * ferait sonner douze fois, et l'alerte qui comptait se perdrait dans le tas.
 * Le trésor y échappe pour la raison même qui fonde la règle — un relevé
 * rapporte au plus **un** mouvement d'argent, jamais douze.
 */
class AlerteTresorTest {

    @get:Rule
    val dossier = TemporaryFolder()

    private fun magasin() = WatchStore(dossier.newFile("guard.json").also { it.delete() })

    private fun mouvementArgent(avant: Long, apres: Long) = MovementStore.Movement(
        at = 1_787_350_189L,
        invKey = MovementStore.MONEY_KEY,
        invLabel = MovementStore.MONEY_LABEL,
        sheet = MovementStore.MONEY_SHEET,
        quality = 0,
        kind = MovementStore.Kind.MODIFIED,
        delta = apres - avant,
        before = avant,
        after = apres,
    )

    private fun mouvementObjet() = MovementStore.Movement(
        at = 1_787_350_189L, invKey = "c1", invLabel = "Coffre 1",
        sheet = "ambre.sitem", quality = 250, kind = MovementStore.Kind.MODIFIED,
        delta = 390, before = 10, after = 400,
    )

    // ------------------------------------------------------------- l'alerte

    @Test
    fun `rien tant que personne n'a demandé`() {
        val alertes = moneyAlerts(
            listOf(mouvementArgent(79_000_000, 78_000_000)), surveille = false)
        assertEquals(emptyList<Alert>(), alertes)
    }

    @Test
    fun `une sortie est annoncée avec son montant`() {
        val alertes = moneyAlerts(
            listOf(mouvementArgent(79_000_000, 78_000_000)), surveille = true)
        assertEquals(1, alertes.size)
        assertEquals(Alert.Kind.MONEY, alertes[0].kind)
        assertTrue(alertes[0].title, "1 000 000" in alertes[0].title)
        assertTrue(alertes[0].title, "sortis" in alertes[0].title)
        assertTrue(alertes[0].detail, "79 000 000" in alertes[0].detail)
        assertTrue(alertes[0].detail, "78 000 000" in alertes[0].detail)
    }

    @Test
    fun `une entrée aussi`() {
        // Dans un sens ou dans l'autre : c'est le mouvement qui compte.
        val alertes = moneyAlerts(
            listOf(mouvementArgent(79_000_000, 79_040_000)), surveille = true)
        assertEquals(1, alertes.size)
        assertTrue(alertes[0].title, "40 000" in alertes[0].title)
        assertTrue(alertes[0].title, "entrés" in alertes[0].title)
    }

    @Test
    fun `les mouvements d'objets restent muets`() {
        // Seul le trésor échappe à la règle ; les objets vont au journal.
        assertEquals(emptyList<Alert>(),
                     moneyAlerts(listOf(mouvementObjet()), surveille = true))
    }

    // -------------------------------------------------------- la surveillance

    @Test
    fun `posée puis levée`() {
        val w = magasin()
        assertFalse(w.isMoneyWatched())
        w.setMoneyWatched(true)
        assertTrue(w.isMoneyWatched())
        w.setMoneyWatched(false)
        assertFalse(w.isMoneyWatched())
    }

    @Test
    fun `elle survit à la fermeture`() {
        // Une surveillance se pose une fois, pas à chaque lancement.
        val fichier = dossier.newFile("garde.json").also { it.delete() }
        WatchStore(fichier).setMoneyWatched(true)
        assertTrue(WatchStore(fichier).isMoneyWatched())
    }

    @Test
    fun `le trésor ne passe pas pour un objet disparu`() {
        // Sans garde, il serait cherché dans les contenants, introuvable, et
        // signalé « disparu » dès le premier relevé.
        val w = magasin()
        w.setMoneyWatched(true)
        val entite = Entity(
            kind = Entity.Kind.GUILD, id = "1", name = "La Lune Eternelle",
            dappers = 79_000_000,
            inventories = listOf(Inventory(
                key = "c1", label = "Coffre 1",
                items = listOf(Item(sheet = "ambre.sitem", id = "a", quality = 250, stack = 5)))),
        )
        assertEquals(emptyList<Alert>(), w.alerts(entite) { it })
        assertTrue(w.isMoneyWatched())        // toujours là
    }

    @Test
    fun `l'entrée porte son genre`() {
        val w = magasin()
        w.setMoneyWatched(true)
        assertEquals(WatchStore.Kind.MONEY,
                     w.all().first { it.signature == WatchStore.MONEY_SIG }.kind)
    }
}
