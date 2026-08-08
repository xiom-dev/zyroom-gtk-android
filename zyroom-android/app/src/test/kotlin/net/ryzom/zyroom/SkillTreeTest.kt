package net.ryzom.zyroom

import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.model.Skill
import net.ryzom.zyroom.model.skillTree
import net.ryzom.zyroom.model.visibleSkills
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File

/**
 * L'arbre déduit des codes, et ce qui se voit selon les replis.
 *
 * Cette logique vit hors de l'écran justement pour être couverte ici : le repli
 * lui-même ne se vérifie qu'à l'œil sur un téléphone.
 */
class SkillTreeTest {

    private fun skills(vararg codes: String) = codes.map { Skill(it, 100) }

    @Test
    fun `la hiérarchie se déduit des préfixes`() {
        val arbre = skillTree(skills("sf", "sfm", "sfms", "sfr")).associateBy { it.skill.code }

        assertEquals(null, arbre["sf"]!!.parent)
        assertEquals(0, arbre["sf"]!!.depth)
        assertTrue(arbre["sf"]!!.hasChildren)

        assertEquals("sf", arbre["sfm"]!!.parent)
        assertEquals(1, arbre["sfm"]!!.depth)

        assertEquals("sfm", arbre["sfms"]!!.parent)
        assertEquals(2, arbre["sfms"]!!.depth)
        assertFalse("une feuille n'a rien à déplier", arbre["sfms"]!!.hasChildren)

        // Tous rattachés à la même racine, quelle que soit la profondeur.
        assertTrue(arbre.values.all { it.root == "sf" })
    }

    /**
     * Le parent est le plus proche des ancêtres. Si l'API saute un échelon —
     * `sfm` absent alors que `sfms` existe —, `sfms` doit se rattacher à `sf`
     * et non se retrouver deux crans trop à droite.
     */
    @Test
    fun `un échelon manquant ne décale pas l'affichage`() {
        val arbre = skillTree(skills("sf", "sfms")).associateBy { it.skill.code }
        assertEquals("sf", arbre["sfms"]!!.parent)
        assertEquals(1, arbre["sfms"]!!.depth)
    }

    @Test
    fun `tout est replié au départ, seules les racines se voient`() {
        val arbre = skillTree(skills("sf", "sfm", "sfms", "sc", "sca"))
        assertEquals(listOf("sc", "sf"),
                     visibleSkills(arbre, emptySet()).map { it.skill.code })
    }

    @Test
    fun `ouvrir une compétence ne montre que ses enfants directs`() {
        val arbre = skillTree(skills("sf", "sfm", "sfms", "sfmd", "sfr"))

        assertEquals(listOf("sf", "sfm", "sfr"),
                     visibleSkills(arbre, setOf("sf")).map { it.skill.code })
        assertEquals(listOf("sf", "sfm", "sfmd", "sfms", "sfr"),
                     visibleSkills(arbre, setOf("sf", "sfm")).map { it.skill.code })
    }

    /**
     * Replier une racine referme tout ce qu'elle contient, sans effacer l'état
     * des échelons du dessous : la rouvrir les retrouve comme on les avait
     * laissés.
     */
    @Test
    fun `replier un parent cache les petits-enfants sans perdre leur état`() {
        val arbre = skillTree(skills("sf", "sfm", "sfms"))
        val ouverts = setOf("sf", "sfm")

        assertEquals(3, visibleSkills(arbre, ouverts).size)
        assertEquals(listOf("sf"), visibleSkills(arbre, ouverts - "sf").map { it.skill.code })
        // « sfm » est resté dans l'ensemble : rouvrir sf remontre son contenu.
        assertEquals(3, visibleSkills(arbre, ouverts).size)
    }

    @Test
    fun `sur le vrai flux, quatre racines et rien d'autre au départ`() {
        val flux = File(System.getProperty("user.home"),
                        ".cache/zyroom-gtk/character/689325.xml")
        assumeTrue("aucun flux personnage en cache", flux.isFile)

        val arbre = skillTree(EntityParser.parseCharacter(flux.readBytes()).skills)
        val racines = visibleSkills(arbre, emptySet())
        assertEquals(listOf("sc", "sf", "sh", "sm"), racines.map { it.skill.code })
        assertTrue("chaque racine doit se déplier", racines.all { it.hasChildren })

        // Ouvrir l'artisanat ne déverse pas ses cent sept descendants.
        val artisanat = visibleSkills(arbre, setOf("sc"))
        assertTrue("trop de lignes d'un coup : ${artisanat.size}", artisanat.size < 12)

        // Et tout ouvrir rend bien l'arbre entier, sans perte ni doublon.
        val tout = visibleSkills(arbre, arbre.map { it.skill.code }.toSet())
        assertEquals(arbre.size, tout.size)
    }
}
