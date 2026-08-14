package net.ryzom.zyroom

import net.ryzom.zyroom.model.CONTINENT_DE_ZONE
import net.ryzom.zyroom.model.POP
import net.ryzom.zyroom.model.SUPREMES
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * La table de pop : ce qui sort, et par quel temps.
 *
 * Elle n'est plus relevée à la main. Elle se déduit de deux sources que l'on
 * peut confronter — le relevé de Ryzom Armory pour le couple saison × zone, et
 * la fourchette d'humidité que le tracker d'atys.us donne pour chaque gisement.
 * Le jeu range l'humidité en quatre bandes et chaque gisement en occupe
 * exactement deux.
 *
 * Les mêmes contrôles existent côté GTK, sur la même table produite par le même
 * générateur : c'est là que la fourchette d'humidité est revérifiée une à une,
 * ce que Kotlin ne peut pas faire sans embarquer le relevé brut.
 */
class PopTest {

    @Test
    fun `les quatre saisons et les quatre zones`() {
        assertEquals(setOf("PRINTEMPS", "ETE", "AUTOMNE", "HIVER"), POP.keys)
        for ((saison, zones) in POP) {
            assertEquals(saison, CONTINENT_DE_ZONE.keys, zones.keys)
        }
    }

    /**
     * Une case vide se lirait « rien ne sort », ce qui n'arrive jamais. C'était
     * le défaut du classeur de la guilde : ses trous ressemblaient à des
     * absences.
     */
    @Test
    fun `les quatre conditions sont partout`() {
        for ((saison, zones) in POP) {
            for ((zone, conditions) in zones) {
                assertEquals(
                    "$saison / $zone",
                    setOf("WORST", "BAD", "GOOD", "BEST"),
                    conditions.keys,
                )
            }
        }
    }

    @Test
    fun `chaque matiere sort par deux conditions`() {
        for ((saison, zones) in POP) {
            for ((zone, conditions) in zones) {
                val compte = mutableMapOf<Pair<String, String>, Int>()
                for (familles in conditions.values) {
                    for ((famille, matieres) in familles) {
                        for (matiere in matieres) {
                            val cle = famille to matiere
                            compte[cle] = (compte[cle] ?: 0) + 1
                        }
                    }
                }
                for ((cle, n) in compte) {
                    assertEquals("$saison / $zone / $cle", 2, n)
                }
            }
        }
    }

    /** Autant de matières distinctes que d'entrées dans le relevé d'Armory. */
    @Test
    fun `la table couvre tout le releve d'Armory`() {
        for ((saison, zones) in POP) {
            for ((zone, conditions) in zones) {
                val distinctes = conditions.values
                    .flatMap { familles -> familles.entries }
                    .flatMap { (famille, matieres) -> matieres.map { famille to it } }
                    .toSet()
                val attendues = SUPREMES[saison]!![zone]!!
                    .entries.sumOf { it.value.size }
                assertEquals("$saison / $zone", attendues, distinctes.size)
            }
        }
    }
}
