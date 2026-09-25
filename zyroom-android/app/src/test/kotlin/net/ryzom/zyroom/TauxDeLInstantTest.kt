package net.ryzom.zyroom

import net.ryzom.zyroom.model.Meteo
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.conditionDe
import net.ryzom.zyroom.model.tauxDeLInstant
import org.junit.Assert.assertEquals
import org.junit.Test

/**
 * L'en-tête affiche le taux que montrent le jeu et la courbe : pendant la
 * dernière heure d'un cycle, il glisse déjà vers le suivant. Relevé du
 * 24 septembre 2026 : 6,7 % puis 71,1 % ; le jeu affichait 53 % à 0,72 h de
 * la fin de la bascule.
 */
class TauxDeLInstantTest {
    private val cycles = listOf(Meteo(41984, "best", 0.067, ""), Meteo(41985, "bad", 0.711, ""))

    private fun releve(heure: Double) = MeteoAtys(
        cycleCourant = (heure / 3).toInt(), heureAtys = heure, saison = 2,
        continents = mapOf("sources" to cycles))

    @Test fun lePalierTientLesDeuxPremieresHeures() =
        assertEquals(0.067, releve(41984 * 3 + 1.5).tauxDeLInstant(cycles)!!, 1e-9)

    @Test fun laDerniereHeureGlisseVersLeSuivant() {
        val taux = releve(41984 * 3 + 2.72).tauxDeLInstant(cycles)!!
        assertEquals(0.53, taux, 0.01)
        assertEquals("bad", conditionDe(taux))
    }

    @Test fun lesSeuilsDuJeu() {
        assertEquals("best", conditionDe(0.10))
        assertEquals("good", conditionDe(0.41))
        assertEquals("bad", conditionDe(0.62))
        assertEquals("worst", conditionDe(0.91))
    }
}
