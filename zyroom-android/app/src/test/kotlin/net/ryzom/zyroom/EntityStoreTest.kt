package net.ryzom.zyroom

import net.ryzom.zyroom.data.EntityStore
import org.junit.Assert.assertEquals
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
}
