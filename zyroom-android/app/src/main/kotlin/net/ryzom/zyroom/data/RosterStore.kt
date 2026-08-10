package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Member
import net.ryzom.zyroom.model.MouvementMembre
import net.ryzom.zyroom.model.diffMembres
import org.json.JSONObject
import java.io.File

/**
 * Le registre du personnel d'une guilde : qui entre, qui sort, qui monte.
 *
 * Même principe que le journal des mouvements et que celui des avant-postes, et
 * pour la même raison : **l'API ne rend qu'un état, jamais une histoire.** Elle
 * donne l'effectif du jour avec les grades ; deux relevés comparés donnent les
 * arrivées, les départs et les promotions.
 *
 * Ce qui se passe entre deux relevés ne se voit donc pas : un joueur recruté
 * puis parti le lendemain, si l'application n'a pas été ouverte entre-temps, ne
 * laisse aucune trace. C'est la limite de tout journal bâti sur des
 * instantanés, et elle vaut mieux que rien — l'API n'a aucune mémoire.
 *
 * Le journal vit dans les fichiers privés et non dans le cache : c'est
 * justement ce que rien ne saura reconstruire.
 */
class RosterStore(private val dir: File) {

    /**
     * Confronte l'effectif au dernier état connu et journalise les mouvements.
     *
     * Au tout premier relevé il n'y a rien à comparer : on enregistre sans rien
     * journaliser, sinon les cent soixante-dix membres passeraient pour autant
     * d'arrivées le jour de l'installation.
     *
     * Un relevé vide n'est jamais comparé : l'API rend parfois une guilde sans
     * son bloc de membres — la clé n'a pas le module, le flux est tronqué — et
     * la guilde entière semblerait alors avoir démissionné.
     */
    suspend fun record(guildId: String, membres: List<Member>): List<MouvementMembre> =
        withContext(Dispatchers.IO) {
            if (membres.isEmpty()) return@withContext emptyList()
            val apres = membres.associate { it.name to it.grade }
            val avant = readSnapshot(guildId)
            val changements = if (avant == null) emptyList()
                              else diffMembres(avant, apres, System.currentTimeMillis() / 1000)
            if (changements.isNotEmpty()) append(guildId, changements)
            writeSnapshot(guildId, apres)
            prune(guildId)
            changements
        }

    /** Le journal, du plus récent au plus ancien, sur les trente derniers jours. */
    suspend fun history(guildId: String): List<MouvementMembre> =
        withContext(Dispatchers.IO) {
            val depuis = System.currentTimeMillis() / 1000 - RETENTION_JOURS * 86400
            lignes(guildId).mapNotNull { ligne ->
                runCatching {
                    val o = JSONObject(ligne)
                    MouvementMembre(
                        at = o.optLong("at"),
                        member = o.optString("member"),
                        kind = o.optString("kind"),
                        from = o.optString("from"),
                        to = o.optString("to"),
                    )
                }.getOrNull()
            }.filter { it.at >= depuis }.sortedByDescending { it.at }
        }

    suspend fun clear(guildId: String) = withContext(Dispatchers.IO) {
        logFile(guildId).delete()
        Unit
    }

    /** Vrai tant qu'aucun relevé n'a été fait : le registre ne peut rien dire. */
    suspend fun jamaisReleve(guildId: String): Boolean = withContext(Dispatchers.IO) {
        !snapFile(guildId).isFile
    }

    // ------------------------------------------------------------- interne

    private fun logFile(id: String) = File(dir, "roster-$id.jsonl")

    private fun snapFile(id: String) = File(dir, "roster-$id.json")

    private fun lignes(id: String): List<String> {
        val file = logFile(id)
        if (!file.isFile) return emptyList()
        return runCatching { file.readLines() }.getOrDefault(emptyList())
            .filter { it.isNotBlank() }
    }

    /**
     * Réécrit le journal sans les lignes de plus de trente jours.
     *
     * **Les lignes gardées sont recopiées telles quelles**, jamais
     * reconstruites à partir de ce qu'on a su lire : une ligne illisible —
     * fichier tronqué par une coupure — disparaîtrait sinon à la réécriture, et
     * une simple erreur de lecture aurait effacé tout l'historique. Ce qu'on ne
     * comprend pas, on le garde : c'est un journal, il n'est pas remplaçable.
     */
    private fun prune(id: String) {
        val depuis = System.currentTimeMillis() / 1000 - RETENTION_JOURS * 86400
        val toutes = lignes(id)
        if (toutes.isEmpty()) return
        var ecartees = 0
        val gardees = toutes.filter { ligne ->
            val at = runCatching { JSONObject(ligne).optLong("at") }.getOrNull()
            if (at == null) true                      // illisible : on n'y touche pas
            else if (at < depuis) { ecartees++; false } else true
        }
        if (ecartees == 0) return
        runCatching {
            logFile(id).writeText(gardees.joinToString("\n", postfix = "\n"))
        }
    }

    private fun readSnapshot(id: String): Map<String, String>? {
        val file = snapFile(id)
        if (!file.isFile) return null
        return runCatching {
            val o = JSONObject(file.readText())
            o.keys().asSequence().associateWith { o.getString(it) }
        }.getOrNull()
    }

    private fun writeSnapshot(id: String, effectif: Map<String, String>) {
        runCatching {
            dir.mkdirs()
            snapFile(id).writeText(JSONObject(effectif as Map<*, *>).toString())
        }
    }

    private fun append(id: String, changements: List<MouvementMembre>) {
        runCatching {
            dir.mkdirs()
            logFile(id).appendText(
                changements.joinToString("") { m ->
                    JSONObject()
                        .put("at", m.at)
                        .put("member", m.member)
                        .put("kind", m.kind)
                        .put("from", m.from)
                        .put("to", m.to)
                        .toString() + "\n"
                }
            )
        }
    }

    companion object {
        /**
         * Combien de temps le journal garde ses lignes, en jours.
         *
         * Un mois : c'est la mémoire utile d'un officier — « qui est arrivé ce
         * mois-ci ? », « qui nous a quittés depuis la dernière guerre
         * d'avant-poste ? ». Au-delà, la liste s'allonge sans que personne la
         * lise.
         */
        const val RETENTION_JOURS = 30L
    }
}
