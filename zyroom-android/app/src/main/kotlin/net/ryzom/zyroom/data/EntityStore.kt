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
        /**
         * L'adresse de l'illustration — rendu 3D du personnage, emblème de la
         * guilde. Retenue ici plutôt que relue du flux : l'écran d'accueil
         * devrait sinon analyser un document d'un méga-octet par carte, juste
         * pour en tirer une URL.
         */
        val vignette: String = "",
        /**
         * Le nom a été choisi à la main, l'API ne le remplace plus.
         *
         * Sans ce drapeau, renommer ne servirait à rien : `rename` recopie le
         * nom du flux à chaque retour sur l'accueil, et le nom donné aurait
         * disparu avant qu'on ait fini de regarder la liste.
         */
        val nomImpose: Boolean = false,
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

    /** Retient ce que l'API vient de dire : le nom, et l'illustration. */
    fun rename(entry: Suivie, label: String, vignette: String = "") {
        val index = entries.indexOfFirst { it.id == entry.id && it.kind == entry.kind }
        if (index < 0) return
        val actuel = entries[index]
        val neuf = actuel.copy(
            // Un nom choisi a la main tient devant celui du flux : c'est tout
            // l'objet de l'avoir choisi. L'illustration, elle, se rafraichit
            // dans tous les cas -- personne ne la saisit.
            label = if (actuel.nomImpose) actuel.label else label,
            // Une URL vide n'efface pas celle qu'on avait : le flux peut être
            // incomplet un jour sans que la vignette doive disparaître.
            vignette = vignette.ifEmpty { actuel.vignette },
        )
        if (neuf != actuel) {
            entries[index] = neuf
            save()
        }
    }

    /**
     * Le nom que l'on donne soi-même à une entité.
     *
     * Vide, il rend la main à l'API : le nom du flux reprend au relevé
     * suivant, et l'on retrouve le comportement d'avant sans avoir à retirer
     * puis ré-ajouter l'entité.
     */
    fun renommer(entry: Suivie, label: String) {
        val index = entries.indexOfFirst { it.id == entry.id && it.kind == entry.kind }
        if (index < 0) return
        val voulu = label.trim()
        entries[index] = entries[index].copy(
            label = voulu.ifEmpty { entries[index].label },
            nomImpose = voulu.isNotEmpty(),
        )
        save()
    }

    /**
     * Remplace la clé d'une entité, la nouvelle ayant déjà été vérifiée.
     *
     * Elle peut désigner une autre entité — on s'est trompé de ligne, ou l'on
     * a repris la clé d'un autre personnage. L'ancienne entrée s'en va alors :
     * sans quoi la liste porterait deux fois la même entité, l'une avec une
     * clé qui n'est plus la sienne.
     */
    fun remplacerCle(ancienne: Suivie, neuve: Suivie) {
        if (ancienne.id != neuve.id || ancienne.kind != neuve.kind) remove(ancienne)
        add(neuve)
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
                    vignette = item.optString("vignette"),
                    nomImpose = item.optBoolean("nomImpose", false),
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
                put("vignette", entry.vignette)
                put("nomImpose", entry.nomImpose)
            })
        }
        file.parentFile?.mkdirs()
        file.writeText(array.toString(2))
    }
}
