package net.ryzom.zyroom

import net.ryzom.zyroom.model.Filtres
import net.ryzom.zyroom.model.Item
import net.ryzom.zyroom.model.ItemClass
import net.ryzom.zyroom.model.ItemEcosystem
import net.ryzom.zyroom.model.ItemEquip
import net.ryzom.zyroom.model.ItemType
import net.ryzom.zyroom.model.Jauge
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Le filtre de la grille d'inventaire.
 *
 * C'est la part du panneau où l'on se trompe : l'interface ne fait que cocher
 * des cases, et un critère qui retire un objet de trop ne se voit pas — le
 * coffre paraît simplement plus vide qu'il n'est.
 *
 * Le cas qui demande le plus d'attention est celui des quatre jauges, dont la
 * règle n'est pas celle des autres groupes : tout coché laisse passer même ce
 * qui ne porte aucun bonus.
 */
class FiltresTest {

    private val jabote = Item(
        sheet = "icfam1pd.sitem", quality = 250, type = ItemType.EQUIPMENT,
        equip = ItemEquip.WEAPON_MELEE, ecosystem = ItemEcosystem.DESERT,
        itemClass = ItemClass.SUPREME, sapBuff = 40,
    )
    private val matiere = Item(
        sheet = "m0117dxapc01.sitem", quality = 200, type = ItemType.NATURAL_MAT,
        ecosystem = ItemEcosystem.COMMON, itemClass = ItemClass.FINE,
    )
    private val casque = Item(
        sheet = "iccah.sitem", quality = 100, type = ItemType.EQUIPMENT,
        equip = ItemEquip.HEAVY_ARMOR, ecosystem = ItemEcosystem.COMMON,
        locked = true, hpBuff = 12,
    )

    private val tout = listOf(jabote, matiere, casque)

    private fun retenus(filtres: Filtres) = tout.filter(filtres::passe)

    // ------------------------------------------------------------ Au repos

    @Test
    fun `au repos rien n'est retire`() {
        assertEquals(tout, retenus(Filtres()))
    }

    @Test
    fun `au repos le filtre ne se dit pas actif`() {
        assertFalse(Filtres().actif)
    }

    // ------------------------------------------------------------- Qualité

    @Test
    fun `la plage de qualite garde ses bornes`() {
        val f = Filtres(qualiteMin = 100, qualiteMax = 200)
        assertEquals(listOf(matiere, casque), retenus(f))
    }

    @Test
    fun `une plage reduite a un point ne garde que ce point`() {
        assertEquals(listOf(casque), retenus(Filtres(qualiteMin = 100, qualiteMax = 100)))
    }

    // ------------------------------------------------------- Interrupteurs

    @Test
    fun `le cadenas ne garde que ce qui est verrouille`() {
        assertEquals(listOf(casque), retenus(Filtres(cadenas = true)))
    }

    @Test
    fun `avec bonus ecarte ce qui n'en porte aucun`() {
        assertEquals(listOf(jabote, casque), retenus(Filtres(avecBonus = true)))
    }

    @Test
    fun `en vente ecarte ce qui n'a pas de date d'expiration`() {
        val enVente = matiere.copy(expires = 1_800_000_000L)
        val f = Filtres(enVente = true)
        assertTrue(f.passe(enVente))
        assertFalse(f.passe(matiere))
    }

    // -------------------------------------------------------- Les groupes

    @Test
    fun `un type decoche disparait`() {
        val f = Filtres(types = ItemType.entries.toSet() - ItemType.EQUIPMENT)
        assertEquals(listOf(matiere), retenus(f))
    }

    @Test
    fun `une classe decochee disparait`() {
        val f = Filtres(classes = ItemClass.entries.toSet() - ItemClass.SUPREME)
        assertEquals(listOf(matiere, casque), retenus(f))
    }

    @Test
    fun `un ecosysteme decoche disparait`() {
        val f = Filtres(ecosystemes = ItemEcosystem.entries.toSet() - ItemEcosystem.DESERT)
        assertEquals(listOf(matiere, casque), retenus(f))
    }

    @Test
    fun `l'emplacement ne qualifie que l'equipement`() {
        // Decocher toutes les cases d'equipement retire les deux pieces, et
        // laisse la matiere : elle n'a pas d'emplacement, ce n'est pas une
        // raison de la faire disparaitre.
        val f = Filtres(equipements = emptySet())
        assertEquals(listOf(matiere), retenus(f))
    }

    // ----------------------------------------------------- Les quatre jauges

    @Test
    fun `toutes les jauges cochees laissent passer meme ce qui n'a aucun bonus`() {
        assertTrue(Filtres().passe(matiere))
    }

    @Test
    fun `une seule jauge cochee ne garde que ce qui la porte`() {
        val f = Filtres(jauges = setOf(Jauge.SEVE))
        assertEquals(listOf(jabote), retenus(f))
    }

    @Test
    fun `deux jauges cochees gardent l'un ou l'autre`() {
        val f = Filtres(jauges = setOf(Jauge.SEVE, Jauge.VIE))
        assertEquals(listOf(jabote, casque), retenus(f))
    }

    @Test
    fun `decocher une seule jauge ecarte deja ce qui n'a pas de bonus`() {
        // Trois cases sur quatre : le groupe cesse d'etre au repos, et la
        // matiere sans bonus tombe avec le reste.
        val f = Filtres(jauges = Jauge.entries.toSet() - Jauge.CONCENTRATION)
        assertEquals(listOf(jabote, casque), retenus(f))
    }

    @Test
    fun `aucune jauge cochee ne garde rien`() {
        assertTrue(retenus(Filtres(jauges = emptySet())).isEmpty())
    }

    // ------------------------------------------------------ Le bouton actif

    @Test
    fun `un critere pose suffit a rendre le filtre actif`() {
        assertTrue(Filtres(cadenas = true).actif)
        assertTrue(Filtres(qualiteMin = 50).actif)
        assertTrue(Filtres(qualiteMax = 200).actif)
        assertTrue(Filtres(jauges = setOf(Jauge.VIE)).actif)
        assertTrue(Filtres(types = emptySet()).actif)
    }

    // ---------------------------------------------------- Plusieurs critères

    @Test
    fun `les criteres se cumulent`() {
        val f = Filtres(
            qualiteMin = 200,
            types = setOf(ItemType.EQUIPMENT),
            jauges = setOf(Jauge.SEVE),
        )
        assertEquals(listOf(jabote), retenus(f))
    }
}
