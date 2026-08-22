package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.model.dateEntree
import net.ryzom.zyroom.model.decrireMouvement
import net.ryzom.zyroom.model.diffMembres
import net.ryzom.zyroom.model.nomGrade
import net.ryzom.zyroom.model.rangGrade
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/** Le registre du personnel, porté de la version GTK. */
class RosterTest {

    @Test
    fun `les grades se disent en français, du chef au membre`() {
        assertEquals("Officier supérieur", nomGrade("HighOfficer"))
        assertEquals("Chef", nomGrade("Leader"))
        assertEquals("Bidule", nomGrade("Bidule"))
        assertEquals("—", nomGrade(""))
        assertTrue(rangGrade("Leader") < rangGrade("Officer"))
        assertTrue(rangGrade("Officer") < rangGrade("Member"))
    }

    /**
     * Liloulove est entrée dans La Lune Eternelle le 17 août 2026 vers 18 h —
     * alors que le journal, bâti sur les seuls relevés, la datait du 19.
     */
    private val LILOULOVE = 8_784_019_565L

    @Test
    fun `la date d'entrée de l'API retombe sur son jour`() {
        val quand = dateEntree(LILOULOVE, 1_787_400_000L)
        val jour = java.time.Instant.ofEpochSecond(quand)
            .atZone(java.time.ZoneId.of("Europe/Paris")).toLocalDate()
        assertEquals("2026-08-17", jour.toString())
    }

    @Test
    fun `dix pas par seconde`() {
        assertEquals(1L, dateEntree(LILOULOVE + 10, 1_787_400_000L)
            - dateEntree(LILOULOVE, 1_787_400_000L))
    }

    /**
     * Champ absent, compteur remis à zéro, horloge locale fausse : mieux vaut
     * zéro — l'appelant retombera sur la date du relevé.
     */
    @Test
    fun `une date d'entrée absurde ne vaut rien`() {
        assertEquals(0L, dateEntree(0L, 1_787_400_000L))
        assertEquals(0L, dateEntree(1_000_000_000_000L, 1_787_400_000L))
    }

    @Test
    fun `l'arrivée porte la date de l'API, le reste celle du relevé`() {
        val entree = dateEntree(LILOULOVE, 1_787_400_000L)
        val vus = diffMembres(
            mapOf("Nizy" to "Officer", "Dale" to "Member"),
            mapOf("Dale" to "Officer", "Liloulove" to "Member"),
            1_787_400_000L,
            mapOf("Liloulove" to entree, "Dale" to entree),
        ).associateBy { it.member }
        assertEquals(entree, vus["Liloulove"]!!.at)
        assertEquals(1_787_400_000L, vus["Nizy"]!!.at)
        assertEquals(1_787_400_000L, vus["Dale"]!!.at)
    }

    /** Une horloge locale en retard la poserait en tête du journal. */
    @Test
    fun `une arrivée ne se date jamais de l'avenir`() {
        val vu = diffMembres(emptyMap(), mapOf("Kiranaa" to "Member"), 100L,
                             mapOf("Kiranaa" to 5_000L)).first()
        assertEquals(100L, vu.at)
    }

    /**
     * Le compteur de l'API dérive ; la fenêtre des deux relevés, non. Un
     * nouveau venu est forcément entré après le relevé qui ne le voyait pas.
     */
    @Test
    fun `l'arrivée ne précède pas le relevé précédent`() {
        val vu = diffMembres(emptyMap(), mapOf("Kiranaa" to "Member"), 1_000L,
                             mapOf("Kiranaa" to 10L), depuis = 900L).first()
        assertEquals(900L, vu.at)
    }

    @Test
    fun `dans la fenêtre, la date de l'API l'emporte`() {
        val vu = diffMembres(emptyMap(), mapOf("Kiranaa" to "Member"), 1_000L,
                             mapOf("Kiranaa" to 950L), depuis = 900L).first()
        assertEquals(950L, vu.at)
    }

    @Test
    fun `arrivée, départ et changement de grade`() {
        val avant = mapOf("Dale" to "Member", "Nizy" to "Officer", "Elanor" to "Member")
        val apres = mapOf("Dale" to "Officer", "Elanor" to "Member", "Kiranaa" to "Member")
        val parNom = diffMembres(avant, apres, 42).associateBy { it.member }

        assertEquals(setOf("Dale", "Nizy", "Kiranaa"), parNom.keys)
        assertEquals("grade", parNom["Dale"]!!.kind)
        assertTrue(parNom["Dale"]!!.promotion)
        assertEquals("depart", parNom["Nizy"]!!.kind)
        assertEquals("arrivee", parNom["Kiranaa"]!!.kind)
    }

    @Test
    fun `une rétrogradation n'est pas une promotion`() {
        val m = diffMembres(mapOf("Dale" to "Officer"), mapOf("Dale" to "Member"), 0).first()
        assertEquals("grade", m.kind)
        assertFalse(m.promotion)
    }

    @Test
    fun `rien ne bouge, rien ne se journalise`() {
        val etat = mapOf("Dale" to "Member")
        assertEquals(emptyList<Any>(), diffMembres(etat, etat, 0))
    }

    @Test
    fun `les lignes se lisent telles quelles`() {
        val arrivee = diffMembres(emptyMap(), mapOf("Kiranaa" to "Member"), 0).first()
        val depart = diffMembres(mapOf("Nizy" to "Officer"), emptyMap(), 0).first()
        assertTrue("a rejoint la guilde" in decrireMouvement(arrivee))
        assertTrue("a quitté la guilde" in decrireMouvement(depart))
        val montee = diffMembres(mapOf("Dale" to "Member"),
                                 mapOf("Dale" to "Officer"), 0).first()
        // Le signe n'est pas dans le texte : l'écran le pose à part, en couleur.
        assertEquals("Dale : Membre → Officier", decrireMouvement(montee))
    }

    @Test
    fun `le flux de guilde rend les membres et leurs grades`() {
        val xml = """<?xml version="1.0"?><ryzomapi><guild><gid>1</gid>
            <name>La Lune</name><members>
              <member><name>Dale</name><grade>Member</grade><joined>611</joined></member>
              <member><name>Nizy</name><grade>Leader</grade><joined>612</joined></member>
              <member><name></name><grade>Member</grade></member>
            </members></guild></ryzomapi>""".toByteArray()
        val guilde = EntityParser.parseGuild(xml)
        assertEquals(2, guilde.members.size)
        assertEquals("Leader", guilde.members.first { it.name == "Nizy" }.grade)
    }

    @Test
    fun `sur le vrai flux, l'effectif est complet et gradé`() {
        val flux = File(System.getProperty("user.home"),
                        ".cache/zyroom-gtk/guild/105906237.xml")
        assumeTrue("aucun flux de guilde en cache", flux.isFile)
        val guilde = EntityParser.parseGuild(flux.readBytes())
        assertTrue("effectif vide : ${guilde.members.size}", guilde.members.size > 100)
        assertEquals(1, guilde.members.count { it.grade == "Leader" })
        assertTrue(guilde.members.all { it.name.isNotBlank() })
    }
}
