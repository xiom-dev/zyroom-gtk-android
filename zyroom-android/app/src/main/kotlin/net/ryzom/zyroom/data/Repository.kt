package net.ryzom.zyroom.data

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.api.ApiException
import net.ryzom.zyroom.api.EntityParser
import net.ryzom.zyroom.api.RyzomApi
import net.ryzom.zyroom.model.Entity
import net.ryzom.zyroom.names.NameDb
import java.io.File
import java.io.InputStream

/**
 * Ce qui va chercher les données et ce qui les garde.
 *
 * Le flux de l'API est écrit tel quel sur le disque : c'est lui qui permet de
 * consulter ses inventaires sans réseau, et c'est de lui qu'on relit la date
 * de fraîcheur. On ne rappelle l'API que si elle a de quoi rendre autre chose,
 * c'est-à-dire une fois `cached_until` dépassé — la version GTK, elle,
 * redemande toutes les quinze minutes quoi qu'il arrive.
 */
class Repository(
    private val cacheDir: File,
    private val store: EntityStore,
) {

    /** Table des noms — un état, pour que les écrans se redessinent à l'import. */
    var names: NameDb by mutableStateOf(NameDb.EMPTY)
        private set

    /**
     * Charge les noms : le pack importé s'il y en a un, celui livré sinon.
     *
     * Deux mégaoctets et demi à parcourir — jamais sur le fil de l'affichage,
     * sous peine de figer l'écran au démarrage comme à l'import.
     */
    suspend fun loadNames(imported: File, bundled: () -> InputStream?) =
        withContext(Dispatchers.IO) {
            names = runCatching {
                if (imported.isFile) NameDb.read(imported)
                else bundled()?.use { NameDb.parse(it.readBytes()) } ?: NameDb.EMPTY
            }.getOrDefault(NameDb.EMPTY)
        }

    fun nameOf(sheet: String): String = names.nameOf(sheet)

    private fun fileFor(entry: EntityStore.Suivie) =
        File(cacheDir, "${entry.kind.name.lowercase()}-${entry.id}.xml")

    /** Ce qu'on a sous la main, sans toucher au réseau. */
    suspend fun cached(entry: EntityStore.Suivie): Entity? = withContext(Dispatchers.IO) {
        val file = fileFor(entry)
        if (!file.isFile) return@withContext null
        runCatching { parse(entry, file.readBytes()) }.getOrNull()
    }

    /**
     * Rend l'entité à jour, en appelant l'API si nécessaire.
     *
     * @param force ignore la date de fraîcheur — c'est le tirer-pour-rafraîchir.
     */
    @Throws(ApiException::class)
    suspend fun refresh(entry: EntityStore.Suivie, force: Boolean = false): Entity =
        withContext(Dispatchers.IO) {
            val known = cached(entry)
            val now = System.currentTimeMillis() / 1000
            if (!force && known != null && !known.isStale(now)) {
                return@withContext known
            }

            val url = when (entry.kind) {
                Entity.Kind.CHARACTER -> RyzomApi.characterUrl(entry.apiKey)
                Entity.Kind.GUILD -> RyzomApi.guildUrl(entry.apiKey)
            }
            val xml = RyzomApi.get(url)
            val entity = parse(entry, xml)

            cacheDir.mkdirs()
            fileFor(entry).writeBytes(xml)
            store.rename(entry, entity.name)
            entity
        }

    /**
     * Interroge l'API sur une poignée de clés, en un appel par espèce.
     *
     * Rend, pour chaque clé qui a répondu, l'entité qu'elle désigne : c'est ce
     * qui permet d'ajouter quatre personnages d'un coup, avec leurs vrais noms.
     */
    @Throws(ApiException::class)
    suspend fun discover(keys: List<String>): List<Pair<String, Entity>> =
        withContext(Dispatchers.IO) {
            val parEspece = keys.mapNotNull { cle ->
                RyzomApi.kindOf(cle)?.let { it to cle }
            }.groupBy({ it.first }, { it.second })

            buildList {
                parEspece.forEach { (espece, cles) ->
                    val url = if (espece == Entity.Kind.CHARACTER)
                        RyzomApi.charactersUrl(cles) else RyzomApi.guildsUrl(cles)
                    val flux = RyzomApi.get(url)
                    EntityParser.parseAll(flux, espece).forEach { (cle, entite) ->
                        add(cle to entite)
                    }
                    // Le flux n'est pas mis en cache : il porte toutes les
                    // entités à la fois, et le cache est nommé par entité. Le
                    // premier affichage ira le chercher pour son compte.
                }
            }
        }

    private fun parse(entry: EntityStore.Suivie, xml: ByteArray): Entity =
        when (entry.kind) {
            Entity.Kind.CHARACTER -> EntityParser.parseCharacter(xml)
            Entity.Kind.GUILD -> EntityParser.parseGuild(xml)
        }
}
