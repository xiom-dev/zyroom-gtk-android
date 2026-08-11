package net.ryzom.zyroom

import net.ryzom.zyroom.model.EXCELLENTES
import net.ryzom.zyroom.model.SAISONS
import net.ryzom.zyroom.model.SUPREMES
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Le relevé figé des matières : ce que l'écran météo suppose de lui.
 *
 * L'écran n'affiche plus qu'une seule liste d'excellentes — celle qui vaut en
 * ce moment, de jour ou de nuit. Il faut donc que les deux existent pour
 * chaque saison : une liste manquante ne donnerait pas une erreur mais un
 * tableau vide, que rien ne distinguerait d'une nuit sans matière excellente.
 */
class ArmoryTableTest {

    @Test
    fun `chaque saison a ses excellentes de jour et de nuit`() {
        SAISONS.forEach { saison ->
            listOf("JOUR", "NUIT").forEach { moment ->
                val groupes = EXCELLENTES[saison]?.get(moment)
                assertTrue("$saison / $moment manque au relevé",
                           !groupes.isNullOrEmpty())
                assertTrue("$saison / $moment ne nomme aucune matière",
                           groupes!!.values.all { it.isNotEmpty() })
            }
        }
    }

    @Test
    fun `chaque saison a ses suprêmes, zone par zone`() {
        SAISONS.forEach { saison ->
            val zones = SUPREMES[saison]
            assertTrue("$saison manque au relevé des suprêmes", !zones.isNullOrEmpty())
            zones!!.forEach { (zone, groupes) ->
                assertTrue("$saison / $zone ne nomme aucune matière",
                           groupes.isNotEmpty() && groupes.values.all { it.isNotEmpty() })
            }
        }
    }

    /**
     * De jour et de nuit, ce ne sont pas les mêmes matières.
     *
     * C'est ce qui justifie de n'en montrer qu'une : si une matière sortait aux
     * deux moments, la cacher la moitié du temps la ferait passer pour
     * indisponible alors qu'elle sort en permanence.
     *
     * La comparaison porte sur les matières, non sur les familles : en été, les
     * Fibres sortent aux deux moments — Buo de jour, Anete, Dzao et Shu de nuit
     * — et comparer les familles ferait crier au recoupement là où il n'y en a
     * pas.
     */
    @Test
    fun `les excellentes de nuit ne sont pas celles du jour`() {
        SAISONS.forEach { saison ->
            fun matieres(moment: String) = EXCELLENTES[saison]?.get(moment).orEmpty()
                .flatMap { (groupe, noms) -> noms.map { "$groupe/$it" } }.toSet()
            val communes = matieres("JOUR") intersect matieres("NUIT")
            assertTrue("$saison : $communes sortent de jour comme de nuit",
                       communes.isEmpty())
        }
    }
}
