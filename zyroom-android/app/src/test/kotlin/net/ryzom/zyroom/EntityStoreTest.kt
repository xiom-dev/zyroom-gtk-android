package net.ryzom.zyroom

import net.ryzom.zyroom.data.EntityStore
import net.ryzom.zyroom.model.Entity
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File

/** Ce que l'application connaît au premier démarrage : rien. */
class EntityStoreTest {

    @get:Rule
    val dossier = TemporaryFolder()

    @Test
    fun `un magasin neuf ne connaît aucune entité`() {
        // La guilde y était pré-inscrite, sa clé d'API voyageant en clair dans
        // chaque APK. Chacun ajoute désormais la sienne.
        val magasin = EntityStore(File(dossier.newFolder(), "entities.json"))
        assertEquals(emptyList<EntityStore.Suivie>(), magasin.all())
    }

    private fun magasin() = EntityStore(File(dossier.newFolder(), "entities.json"))

    private fun xiom(cle: String = "c" + "0".repeat(40)) = EntityStore.Suivie(
        id = "689325", kind = Entity.Kind.CHARACTER, apiKey = cle, label = "Xiom")

    @Test
    fun `les personnages passent devant les guildes, chacun par ordre alphabetique`() {
        // Et non l'ordre d'ajout : on cherche un nom dans la liste, pas le
        // souvenir de l'ordre dans lequel on a colle les cles.
        val m = magasin()
        m.add(EntityStore.Suivie("3", Entity.Kind.GUILD, "g3", "Rod Of Heaven"))
        m.add(EntityStore.Suivie("1", Entity.Kind.CHARACTER, "c1", "Zoe"))
        m.add(EntityStore.Suivie("4", Entity.Kind.GUILD, "g4", "La Lune Eternelle"))
        m.add(EntityStore.Suivie("2", Entity.Kind.CHARACTER, "c2", "adrien"))

        assertEquals(
            listOf("adrien", "Zoe", "La Lune Eternelle", "Rod Of Heaven"),
            m.all().map { it.label })
    }

    @Test
    fun `une entite sans nom se classe sur son identifiant`() {
        // L'API n'a pas encore repondu : c'est l'identifiant que la carte
        // affiche, c'est donc lui qui doit servir a la ranger.
        val m = magasin()
        m.add(EntityStore.Suivie("999", Entity.Kind.CHARACTER, "c9", ""))
        m.add(EntityStore.Suivie("111", Entity.Kind.CHARACTER, "c1", "Adrien"))
        // « 999 » passe devant « Adrien » : les chiffres precedent les
        // lettres. Ce qui compte ici est qu'il soit range sur son
        // identifiant et non rejete en fin de liste comme un nom vide.
        assertEquals(listOf("999", "Adrien"),
                     m.all().map { it.label.ifEmpty { it.id } })
    }

    @Test
    fun `un nom choisi a la main tient devant celui du flux`() {
        // Sans quoi renommer ne servirait a rien : l'accueil recopie le nom du
        // flux a chaque retour au premier plan, et le nom donne aurait disparu
        // avant qu'on ait fini de regarder la liste.
        val m = magasin()
        m.add(xiom())
        m.renommer(m.all().first(), "Mon perso de forage")
        m.rename(m.all().first(), "Xiom", "https://exemple/vignette.png")
        assertEquals("Mon perso de forage", m.all().first().label)
        assertTrue(m.all().first().nomImpose)
        // L'illustration, elle, se rafraichit dans tous les cas.
        assertEquals("https://exemple/vignette.png", m.all().first().vignette)
    }

    @Test
    fun `un nom vide rend la main a l'API`() {
        val m = magasin()
        m.add(xiom())
        m.renommer(m.all().first(), "Bidule")
        m.renommer(m.all().first(), "   ")
        assertFalse(m.all().first().nomImpose)
        m.rename(m.all().first(), "Xiom")
        assertEquals("Xiom", m.all().first().label)
    }

    @Test
    fun `le nom impose survit a la relecture du fichier`() {
        val fichier = File(dossier.newFolder(), "entities.json")
        EntityStore(fichier).let {
            it.add(xiom())
            it.renommer(it.all().first(), "Mon perso de forage")
        }
        val relu = EntityStore(fichier)
        assertEquals("Mon perso de forage", relu.all().first().label)
        assertTrue(relu.all().first().nomImpose)
    }

    @Test
    fun `remplacer la cle d'une meme entite ne la duplique pas`() {
        val m = magasin()
        m.add(xiom("c" + "0".repeat(40)))
        val neuve = xiom("c" + "1".repeat(40))
        m.remplacerCle(m.all().first(), neuve)
        assertEquals(1, m.all().size)
        assertEquals("c" + "1".repeat(40), m.all().first().apiKey)
    }

    @Test
    fun `une cle qui designe une autre entite remplace l'ancienne`() {
        // On s'est trompe de ligne, ou l'on a repris la cle d'un autre
        // personnage : la liste porterait sinon deux fois la meme entite,
        // l'une avec une cle qui n'est plus la sienne.
        val m = magasin()
        m.add(xiom())
        val autre = EntityStore.Suivie(
            id = "999999", kind = Entity.Kind.CHARACTER,
            apiKey = "c" + "2".repeat(40), label = "Quelqu'un d'autre")
        m.remplacerCle(m.all().first(), autre)
        assertEquals(1, m.all().size)
        assertEquals("999999", m.all().first().id)
    }
}
