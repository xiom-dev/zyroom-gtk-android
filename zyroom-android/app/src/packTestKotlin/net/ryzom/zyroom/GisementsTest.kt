package net.ryzom.zyroom

import net.ryzom.zyroom.model.EXCELLENTES
import net.ryzom.zyroom.model.Gisements
import net.ryzom.zyroom.model.POP
import net.ryzom.zyroom.model.SUPREMES
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * Les cartes de gisements : la table, et ce qu'elle promet.
 *
 * Le piège de cette table est qu'elle échoue en silence. Une matière mal
 * rapprochée n'affiche pas d'erreur : elle affiche **la carte de la voisine**,
 * et personne ne s'en aperçoit avant d'avoir traversé les Primes pour rien.
 *
 * D'où ces contrôles : chaque libellé affiché mène quelque part, et les deux
 * façons de nommer une même matière — le français du relevé de la guilde et
 * l'anglais des listes de suprêmes — mènent au même endroit.
 */
class GisementsTest {

    /** Tous les couples (famille, matière) que l'écran météo peut écrire. */
    private fun libellesAffiches(): Set<Pair<String, String>> {
        val paires = mutableSetOf<Pair<String, String>>()
        POP.values.forEach { zones ->
            zones.values.forEach { conditions ->
                conditions.values.forEach { familles ->
                    familles.forEach { (famille, matieres) ->
                        matieres.forEach { paires += famille to it }
                    }
                }
            }
        }
        listOf(SUPREMES, EXCELLENTES).forEach { table ->
            table.values.forEach { saison ->
                saison.values.forEach { groupes ->
                    groupes.forEach { (famille, matieres) ->
                        matieres.forEach { paires += famille to it }
                    }
                }
            }
        }
        return paires
    }

    @Test
    fun `tout libelle affiche est connu de la table`() {
        val inconnus = (libellesAffiches() - Gisements.LIBELLES.keys).sortedBy {
            it.first + it.second
        }
        assertEquals(
            "l'écran affiche des matières que la table ignore ; " +
                "relance outils/table_gisements.py",
            emptyList<Pair<String, String>>(), inconnus,
        )
    }

    @Test
    fun `tout libelle mene a une carte`() {
        val muets = Gisements.LIBELLES.keys.filter { (famille, matiere) ->
            Gisements.cartes("supreme", famille, matiere).isEmpty() &&
                Gisements.cartes("excellent", famille, matiere).isEmpty()
        }
        assertEquals(emptyList<Pair<String, String>>(), muets)
    }

    @Test
    fun `le trou du tracker sur la resine Fung est connu`() {
        // Le site n'a aucune vue pour la résine Fung suprême, alors que le
        // relevé de la guilde la donne dans les Sources. C'est un trou du site,
        // pas du rapprochement : on le fige pour que le jour où il se comble,
        // le test le dise.
        assertTrue(Gisements.cartes("supreme", "Résine", "Fung").isEmpty())
        assertTrue(Gisements.cartes("excellent", "Résine", "Fung").isNotEmpty())
    }

    @Test
    fun `les deux noms d'une matiere donnent les memes cartes`() {
        val paires = listOf(
            Triple("Carapace", "Grosse", "Big"),
            Triple("Carapace", "Mignonne", "Cuty"),
            Triple("Carapace", "Inteligente", "Smart"),
            Triple("Carapace", "Cornée", "Horny"),
            Triple("Résine", "Colle", "Glue"),
            Triple("Résine", "Lune", "Moon"),
            Triple("Sève", "Ardente", "Redhot"),
            Triple("Fibres", "Anète", "Anete"),
            Triple("Boucles", "Scratch", "Scrath"),
        )
        for ((famille, francais, anglais) in paires) {
            for (qualite in listOf("supreme", "excellent")) {
                assertEquals(
                    "$francais et $anglais devraient mener au même endroit",
                    Gisements.cartes(qualite, famille, francais),
                    Gisements.cartes(qualite, famille, anglais),
                )
            }
        }
    }

    @Test
    fun `les annotations des joueurs sont suivies`() {
        val annotes = listOf(
            Triple("Ambres", "Beng Agro", "Beng"),
            Triple("Boucles", "Yana ?", "Yana"),
            Triple("Sève", "Ardente ?", "Ardente"),
            Triple("Sève", "Visc agro KKT", "Visc"),
            Triple("Carapace", "Migno Omg AGGRO", "Mignonne"),
        )
        for ((famille, annote, propre) in annotes) {
            assertEquals(
                Gisements.cartes("supreme", famille, propre),
                Gisements.cartes("supreme", famille, annote),
            )
        }
    }

    @Test
    fun `une matiere inconnue ne rend rien`() {
        assertTrue(Gisements.cartes("supreme", "Ambres", "Zorglub").isEmpty())
        assertTrue(Gisements.cartes("supreme", "Zorglub", "Beng").isEmpty())
    }

    @Test
    fun `les fourchettes d'humidite sont plausibles`() {
        for (gisement in Gisements.TABLE.values) {
            assertTrue(gisement.images.isNotEmpty())
            for ((bas, haut) in gisement.humidites) {
                assertTrue(bas >= 0f)
                assertTrue(bas < haut)
                assertTrue(haut <= 100f)
            }
        }
    }
}
