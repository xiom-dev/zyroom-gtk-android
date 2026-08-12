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
            Gisements.points("supreme", famille, matiere).isEmpty() &&
                Gisements.points("excellent", famille, matiere).isEmpty()
        }
        assertEquals(emptyList<Pair<String, String>>(), muets)
    }

    @Test
    fun `le trou du tracker sur la resine Fung est comble`() {
        // Le tracker n'avait aucune vue pour la résine Fung suprême, alors que
        // le relevé de la guilde la donne dans les Sources. Le relevé de
        // Ballistic Mystix, lui, l'a.
        assertTrue(Gisements.points("supreme", "Résine", "Fung").isNotEmpty())
        assertTrue(Gisements.points("excellent", "Résine", "Fung").isNotEmpty())
    }

    @Test
    fun `chaque position porte un nom de lieu`() {
        val sans = mutableListOf<String>()
        for (qualite in listOf("supreme", "excellent")) {
            for ((famille, matiere) in Gisements.LIBELLES.keys) {
                for (point in Gisements.points(qualite, famille, matiere)) {
                    if (point.lieu.isEmpty() || point.lieu.startsWith("region_")) {
                        sans += "$famille/$matiere « ${point.lieu} »"
                    }
                }
            }
        }
        assertEquals(emptyList<String>(), sans.sorted().distinct())
    }

    @Test
    fun `les supremes sont dans les quatre zones du classeur`() {
        val lieux = Gisements.LIBELLES.keys.flatMap { (f, m) ->
            Gisements.points("supreme", f, m).map { it.lieu }
        }.toSet()
        assertEquals(
            setOf("Sources Interdites", "Terre de la Continuité",
                  "Cité Engloutie", "Profondeurs Interdites"),
            lieux,
        )
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
                    Gisements.points(qualite, famille, francais),
                    Gisements.points(qualite, famille, anglais),
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
                Gisements.points("supreme", famille, propre),
                Gisements.points("supreme", famille, annote),
            )
        }
    }

    @Test
    fun `une matiere inconnue ne rend rien`() {
        assertTrue(Gisements.points("supreme", "Ambres", "Zorglub").isEmpty())
        assertTrue(Gisements.points("supreme", "Zorglub", "Beng").isEmpty())
    }

    @Test
    fun `les fourchettes d'humidite sont plausibles`() {
        for (gisement in Gisements.TABLE.values) {
            assertTrue(gisement.points.isNotEmpty())
            for ((bas, haut) in gisement.humidites) {
                assertTrue(bas >= 0f)
                assertTrue(bas < haut)
                assertTrue(haut <= 100f)
            }
        }
    }
}
