package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * Les bonus de craft, ceux que la grille montre par une goutte de couleur.
 *
 * Ils vivent sous `<craftparameters>` et non à la racine de l'item : c'est
 * l'erreur qui les rendait invisibles côté Android, alors que le même flux les
 * donnait à la version GTK.
 */
class SpecialitesTest {

    private val fluxEquipement = """
        <?xml version="1.0"?>
        <ryzomapi version="1.0">
          <character created="1785853247" cached_until="1785920366" modules="C01">
            <id>689325</id>
            <name>Xiom</name>
            <shard>atys</shard>
            <bag>
              <item id="7288895506647062706" slot="1">
                <sheet>icokamm1sa_1.sitem</sheet>
                <quality>250</quality>
                <stack>1</stack>
                <locked>0</locked>
                <hp>113</hp>
                <craftparameters>
                  <durability value="154">0.53</durability>
                  <sapload value="1769">0.70</sapload>
                  <hpbuff>125</hpbuff>
                  <sapbuff>20</sapbuff>
                </craftparameters>
              </item>
              <item id="7288895506647062707" slot="2">
                <sheet>m0117dxajd01.sitem</sheet>
                <quality>250</quality>
                <stack>42</stack>
              </item>
            </bag>
          </character>
        </ryzomapi>
    """.trimIndent().toByteArray()

    private fun items() =
        EntityParser.parseCharacter(fluxEquipement).inventories.first().items

    @Test
    fun `les quatre bonus sont lus sous craftparameters`() {
        val arme = items().first()
        assertEquals(125, arme.hpBuff)
        assertEquals(20, arme.sapBuff)
        assertEquals(0, arme.staBuff)
        assertEquals(0, arme.focusBuff)
    }

    @Test
    fun `une matière n'a aucun bonus`() {
        val matiere = items()[1]
        assertEquals(0, matiere.hpBuff)
        assertEquals(0, matiere.sapBuff)
        assertEquals(0, matiere.staBuff)
        assertEquals(0, matiere.focusBuff)
    }

    @Test
    fun `la durabilité et la qualité restent lues`() {
        // parseItem ne lit plus <craftparameters> qu'une fois, pour la couleur
        // comme pour les bonus : le reste de l'item ne doit pas en pâtir.
        val arme = items().first()
        assertEquals(250, arme.quality)
        assertEquals(113, arme.hp)
    }
}
