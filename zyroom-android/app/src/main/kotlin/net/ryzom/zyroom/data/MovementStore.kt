package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Entity
import org.json.JSONObject
import java.io.File

/**
 * Le journal des mouvements : ce qui est entré et sorti des contenants.
 *
 * Porté de `zyroom/movements.py`, lui-même repris de la fenêtre d'alerte du
 * Delphi d'origine (atAdded / atRemoved / atModified).
 *
 * L'API de Ryzom ne fournit **aucun historique** : elle ne renvoie qu'un état.
 * Les mouvements se déduisent donc de la comparaison de deux états successifs,
 * et seul ce qui a bougé entre deux relevés est vu — deux mouvements qui
 * s'annulent entre-temps passent inaperçus. C'était déjà la limite de
 * l'original.
 *
 * Deux fichiers par entité : l'instantané du dernier état connu, et le journal
 * en JSON Lines. Le journal vit dans les fichiers privés et non dans le cache,
 * parce que c'est justement ce que l'API ne saura pas reconstruire — vider le
 * cache ne doit pas l'effacer.
 */
class MovementStore(private val dir: File) {

    enum class Kind { ADDED, REMOVED, MODIFIED }

    data class Movement(
        /** Secondes Unix, comme le journal de la version GTK. */
        val at: Long,
        val invKey: String,
        val invLabel: String,
        val sheet: String,
        val quality: Int,
        val kind: Kind,
        /** Quantité entrée (positive) ou sortie (négative). */
        val delta: Int,
        val before: Int,
        val after: Int,
    )

    /**
     * Confronte l'entité au dernier état connu, ajoute ce qui a bougé au
     * journal, et retient le nouvel état.
     *
     * Au tout premier relevé il n'y a rien à comparer : on enregistre l'état
     * sans rien journaliser, sinon l'inventaire entier passerait pour un
     * arrivage.
     */
    suspend fun record(entry: EntityStore.Suivie, entity: Entity): List<Movement> =
        withContext(Dispatchers.IO) {
            val avant = readSnapshot(entry)
            val apres = snapshotOf(entity)
            val mouvements = if (avant == null) emptyList()
                             else diff(avant, apres, entity)
            if (mouvements.isNotEmpty()) appendLog(entry, mouvements)
            writeSnapshot(entry, apres)
            mouvements
        }

    /** Le journal, de la relève la plus récente à la plus ancienne. */
    suspend fun history(entry: EntityStore.Suivie): List<Movement> =
        withContext(Dispatchers.IO) {
            val file = logFile(entry)
            if (!file.isFile) return@withContext emptyList()
            val lignes = runCatching { file.readLines() }.getOrDefault(emptyList())
            lignes.mapNotNull { ligne ->
                if (ligne.isBlank()) null
                else runCatching { fromJson(JSONObject(ligne)) }.getOrNull()
            }
                // Tri stable sur le seul horodatage : les relèves ressortent de
                // la plus récente à la plus ancienne, mais à l'intérieur de
                // l'une d'elles l'ordre d'écriture est conservé. Lire le fichier
                // à l'envers retournerait aussi cet ordre-là.
                .sortedByDescending { it.at }
        }

    suspend fun clear(entry: EntityStore.Suivie) = withContext(Dispatchers.IO) {
        logFile(entry).delete()
        Unit
    }

    // ------------------------------------------------------------- interne

    private fun base(entry: EntityStore.Suivie) =
        "${entry.kind.name.lowercase()}-${entry.id}"

    private fun logFile(entry: EntityStore.Suivie) = File(dir, "${base(entry)}.jsonl")

    private fun snapFile(entry: EntityStore.Suivie) = File(dir, "${base(entry)}-etat.json")

    /** `{clé du contenant: {fiche|qualité: quantité}}` */
    private fun snapshotOf(entity: Entity): Map<String, Map<String, Int>> =
        entity.inventories.associate { inventaire ->
            val comptes = mutableMapOf<String, Int>()
            inventaire.items.forEach { item ->
                val signature = WatchStore.signatureOf(item)
                comptes[signature] = (comptes[signature] ?: 0) + maxOf(item.stack, 1)
            }
            inventaire.key to comptes
        }

    private fun diff(
        avant: Map<String, Map<String, Int>>,
        apres: Map<String, Map<String, Int>>,
        entity: Entity,
    ): List<Movement> {
        val maintenant = System.currentTimeMillis() / 1000
        val libelles = entity.inventories.associate { it.key to it.label }
        val out = mutableListOf<Movement>()

        // Seuls les contenants du nouvel état sont examinés : un contenant
        // disparu — une bête vendue — ne doit pas faire croire que tout son
        // contenu vient d'être retiré.
        apres.forEach { (cle, comptesApres) ->
            val comptesAvant = avant[cle].orEmpty()
            (comptesApres.keys + comptesAvant.keys).forEach { signature ->
                val depuis = comptesAvant[signature] ?: 0
                val vers = comptesApres[signature] ?: 0
                if (depuis == vers) return@forEach
                val fiche = signature.substringBeforeLast('|', signature)
                val qualite = signature.substringAfterLast('|', "").toIntOrNull() ?: 0
                out += Movement(
                    at = maintenant,
                    invKey = cle,
                    invLabel = libelles[cle] ?: cle,
                    sheet = fiche,
                    quality = qualite,
                    kind = when {
                        depuis == 0 -> Kind.ADDED
                        vers == 0 -> Kind.REMOVED
                        else -> Kind.MODIFIED
                    },
                    delta = vers - depuis,
                    before = depuis,
                    after = vers,
                )
            }
        }
        // Entrées d'abord, puis sorties, groupées par contenant : l'ordre le
        // plus lisible quand une relève en rapporte beaucoup d'un coup.
        return out.sortedWith(compareBy({ it.invKey }, { -it.delta }))
    }

    private fun appendLog(entry: EntityStore.Suivie, mouvements: List<Movement>) {
        runCatching {
            dir.mkdirs()
            val file = logFile(entry)
            file.appendText(mouvements.joinToString("") { toJson(it).toString() + "\n" })
            trim(file)
        }
    }

    /** Au-delà de [MAX_LINES] lignes, on ne garde que les [KEEP_LINES] dernières. */
    private fun trim(file: File) {
        runCatching {
            val lignes = file.readLines()
            if (lignes.size <= MAX_LINES) return
            file.writeText(lignes.takeLast(KEEP_LINES).joinToString("\n", postfix = "\n"))
        }
    }

    private fun readSnapshot(entry: EntityStore.Suivie): Map<String, Map<String, Int>>? {
        val file = snapFile(entry)
        if (!file.isFile) return null
        return runCatching {
            val racine = JSONObject(file.readText())
            racine.keys().asSequence().associateWith { cle ->
                val contenant = racine.getJSONObject(cle)
                contenant.keys().asSequence()
                    .associateWith { contenant.getInt(it) }
            }
        }.getOrNull()
    }

    private fun writeSnapshot(
        entry: EntityStore.Suivie,
        etat: Map<String, Map<String, Int>>,
    ) {
        runCatching {
            dir.mkdirs()
            val racine = JSONObject()
            etat.forEach { (cle, comptes) ->
                racine.put(cle, JSONObject().apply {
                    comptes.forEach { (signature, quantite) -> put(signature, quantite) }
                })
            }
            snapFile(entry).writeText(racine.toString())
        }
    }

    private fun toJson(m: Movement) = JSONObject().apply {
        put("at", m.at)
        put("inv", m.invKey)
        put("label", m.invLabel)
        put("sheet", m.sheet)
        put("q", m.quality)
        put("kind", m.kind.name)
        put("delta", m.delta)
        put("before", m.before)
        put("after", m.after)
    }

    private fun fromJson(o: JSONObject) = Movement(
        at = o.optLong("at"),
        invKey = o.optString("inv"),
        invLabel = o.optString("label"),
        sheet = o.optString("sheet"),
        quality = o.optInt("q"),
        kind = runCatching { Kind.valueOf(o.optString("kind")) }.getOrDefault(Kind.MODIFIED),
        delta = o.optInt("delta"),
        before = o.optInt("before"),
        after = o.optInt("after"),
    )

    companion object {
        private const val MAX_LINES = 20_000
        private const val KEEP_LINES = 10_000

        /** Ligne rédigée, sur le modèle de l'original. */
        fun describe(m: Movement, nameOf: (String) -> String): String {
            val nom = nameOf(m.sheet)
            val qualite = if (m.quality > 0) " Q${m.quality}" else ""
            return when (m.kind) {
                Kind.ADDED -> "l'objet $nom$qualite a été ajouté (${m.after})"
                Kind.REMOVED -> "l'objet $nom$qualite a été retiré (${m.before})"
                Kind.MODIFIED ->
                    "la quantité de l'objet $nom$qualite a changé (${m.before} > ${m.after})"
            }
        }
    }
}
