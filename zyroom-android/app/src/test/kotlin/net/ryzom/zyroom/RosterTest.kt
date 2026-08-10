package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
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
