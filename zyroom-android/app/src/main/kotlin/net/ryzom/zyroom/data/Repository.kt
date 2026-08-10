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
import net.ryzom.zyroom.model.CONTINENT_DE_ZONE
import net.ryzom.zyroom.model.MeteoAtys
import net.ryzom.zyroom.model.Outpost
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

    private companion object {
        /** Une heure : un avant-poste change de main au rythme des sièges. */
        const val FRAICHEUR_CARTE_MS = 3_600_000L
    }

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
                // Même sans appel réseau, on retient ce que le cache sait : le
                // nom et l'illustration. Sans cela, une entité dont le document
                // reste frais n'aurait jamais de vignette — c'est au moment de
                // l'appel qu'elle était notée, et cet appel n'a pas lieu.
                store.rename(entry, known.name, known.portraitUrl)
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
            store.rename(entry, entity.name, entity.portraitUrl)
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

    /**
     * La carte des avant-postes, sans clé d'API.
     *
     * Un demi-méga-octet, que l'on garde une heure : la propriété d'un
     * avant-poste change au rythme des sièges, pas des minutes. En cas d'échec
     * réseau on rend ce qu'on a sur le disque plutôt que rien — la carte de la
     * veille vaut mieux qu'un écran vide.
     */
    @Throws(ApiException::class)
    suspend fun outposts(force: Boolean = false): List<Outpost> = withContext(Dispatchers.IO) {
        val file = File(cacheDir, "guilds.xml")
        val age = System.currentTimeMillis() - file.lastModified()
        if (!force && file.isFile && age < FRAICHEUR_CARTE_MS) {
            runCatching { EntityParser.parseOutposts(file.readBytes()) }
                .getOrNull()?.let { return@withContext it }
        }
        val xml = try {
            RyzomApi.get(RyzomApi.guildDirectoryUrl())
        } catch (echec: ApiException) {
            if (file.isFile) {
                runCatching { EntityParser.parseOutposts(file.readBytes()) }
                    .getOrNull()?.let { return@withContext it }
            }
            throw echec
        }
        val carte = EntityParser.parseOutposts(xml)
        cacheDir.mkdirs()
        file.writeBytes(xml)
        carte
    }

    /**
     * La météo d'Atys et la saison, prises à l'API officielle.
     *
     * Rien n'est mis en cache sur le disque : le document est minuscule, il
     * change toutes les neuf minutes, et une prévision périmée vaut moins que
     * pas de prévision du tout — l'écran ne s'ouvre que quand on le demande.
     */
    @Throws(ApiException::class)
    suspend fun meteo(cycles: Int = 20): MeteoAtys = withContext(Dispatchers.IO) {
        val continents = CONTINENT_DE_ZONE.values.distinct()
        // Quelques cycles passés en plus : sans eux la courbe commence à
        // l'instant présent, et le trait du « maintenant » se colle au bord.
        val brut = String(RyzomApi.get(RyzomApi.weatherUrl(continents, cycles, passes = 6)))
        val (cycle, heure, parContinent) = EntityParser.parseWeather(brut)
        // La saison vient d'un autre appel : le flux météo ne la porte pas, et
        // c'est elle qui dit quelle page du relevé regarder.
        val saison = runCatching {
            EntityParser.parseSeason(RyzomApi.get(RyzomApi.timeUrl().replace("json", "xml")))
        }.getOrDefault(-1)
        MeteoAtys(cycleCourant = cycle, heureAtys = heure, saison = saison,
                  continents = parContinent)
    }

    private fun parse(entry: EntityStore.Suivie, xml: ByteArray): Entity =
        when (entry.kind) {
            Entity.Kind.CHARACTER -> EntityParser.parseCharacter(xml)
            Entity.Kind.GUILD -> EntityParser.parseGuild(xml)
        }
}
