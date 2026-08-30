package net.ryzom.zyroom

import net.ryzom.zyroom.ui.poigneeDefilement
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * La poignée de la barre de défilement du journal.
 *
 * Compose ne fournit rien pour les listes paresseuses : la géométrie est à
 * notre charge, et c'est la seule part où l'on se trompe. Un journal de mille
 * lignes se parcourt à l'aveugle sans elle.
 */
class BarreDefilementTest {

    /** Un écran de 1000 px sur un journal de 10 000 px : un dixième visible. */
    private val vue = 1000f
    private val total = 10_000f

    @Test
    fun `la hauteur dit quelle part du journal tient a l'ecran`() {
        val poignee = poigneeDefilement(vue, total, defile = 0f, minimum = 28f)
        assertEquals(100f, poignee.hauteur, 0.01f)
    }

    @Test
    fun `en haut du journal la poignee touche le haut`() {
        assertEquals(0f, poigneeDefilement(vue, total, 0f, 28f).haut, 0.01f)
    }

    @Test
    fun `tout en bas la poignee touche le bas`() {
        val poignee = poigneeDefilement(vue, total, defile = total - vue, minimum = 28f)
        assertEquals(vue - poignee.hauteur, poignee.haut, 0.01f)
    }

    @Test
    fun `au milieu elle est au milieu`() {
        val poignee = poigneeDefilement(vue, total, defile = (total - vue) / 2f, minimum = 28f)
        assertEquals((vue - poignee.hauteur) / 2f, poignee.haut, 0.01f)
    }

    @Test
    fun `un journal enorme garde une poignee saisissable`() {
        val poignee = poigneeDefilement(vue, hauteurTotale = 1_000_000f, defile = 0f, minimum = 28f)
        assertEquals(28f, poignee.hauteur, 0.01f)
    }

    @Test
    fun `la poignee ne sort jamais de la glissiere`() {
        // Un defilement au-dela du fond -- l'elastique d'Android -- ne doit pas
        // pousser la poignee hors de l'ecran.
        val poignee = poigneeDefilement(vue, total, defile = total * 2f, minimum = 28f)
        assertTrue(poignee.haut + poignee.hauteur <= vue + 0.01f)
    }

    @Test
    fun `une liste qui tient juste a l'ecran ne divise pas par zero`() {
        val poignee = poigneeDefilement(vue, hauteurTotale = vue, defile = 0f, minimum = 28f)
        assertEquals(vue, poignee.hauteur, 0.01f)
        assertEquals(0f, poignee.haut, 0.01f)
    }
}
