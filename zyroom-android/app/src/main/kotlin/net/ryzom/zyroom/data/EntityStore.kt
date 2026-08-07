package net.ryzom.zyroom.data

import net.ryzom.zyroom.model.Entity
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Les entités suivies et leurs clés d'API, gardées dans un simple JSON.
 *
 * La version GTK emploie deux fichiers INI, `characters.ini` et `guilds.ini` ;
 * ici un seul fichier suffit, l'espèce étant un champ. La clé y est en clair,
 * comme sur le bureau : chacun y met la sienne, il n'y a rien à cacher qu'un
 * accès en lecture à son propre inventaire.
 */
class EntityStore(private val file: File) {

    data class Suivie(
        val id: String,
        val kind: Entity.Kind,
        val apiKey: String,
        val label: String = "",
    )

    private val entries = mutableListOf<Suivie>()

    init {
        // Rien n'est pré-configuré. La guilde l'était : sa clé d'API partait
        // alors en clair dans chaque APK, donnant à tout installateur un accès
        // en lecture à ses inventaires. Elle se transmet désormais sur le
        // Discord de la guilde, et chacun l'ajoute comme il ajoute son
        // personnage.
        load()
    }

    fun all(): List<Suivie> = entries.toList()

    fun add(entry: Suivie) {
        entries.removeAll { it.id == entry.id && it.kind == entry.kind }
        entries += entry
        save()
    }

    fun remove(entry: Suivie) {
        entries.removeAll { it.id == entry.id && it.kind == entry.kind }
        save()
    }

    /** Renomme une entité une fois que l'API a dit comment elle s'appelle. */
    fun rename(entry: Suivie, label: String) {
        val index = entries.indexOfFirst { it.id == entry.id && it.kind == entry.kind }
        if (index >= 0 && entries[index].label != label) {
            entries[index] = entries[index].copy(label = label)
            save()
        }
    }

    private fun load() {
        entries.clear()
        if (!file.isFile) return
        runCatching {
            val array = JSONArray(file.readText())
            for (index in 0 until array.length()) {
                val item = array.getJSONObject(index)
                entries += Suivie(
                    id = item.getString("id"),
                    kind = Entity.Kind.valueOf(item.getString("kind")),
                    apiKey = item.getString("key"),
                    label = item.optString("label"),
                )
            }
        }
    }

    private fun save() {
        val array = JSONArray()
        entries.forEach { entry ->
            array.put(JSONObject().apply {
                put("id", entry.id)
                put("kind", entry.kind.name)
                put("key", entry.apiKey)
                put("label", entry.label)
            })
        }
        file.parentFile?.mkdirs()
        file.writeText(array.toString(2))
    }
}
