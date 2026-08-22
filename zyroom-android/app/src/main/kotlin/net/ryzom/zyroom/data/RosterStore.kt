package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Member
import net.ryzom.zyroom.model.MouvementMembre
import net.ryzom.zyroom.model.dateEntree
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
 * Les **arrivées** font exception depuis le 22 août 2026 : le flux porte pour
 * chaque membre sa date d'entrée, et l'on sait maintenant la lire (voir
 * `ORIGINE_JOINED`). Une arrivée est donc datée du jour où elle a eu lieu, et
 * non du jour où l'application l'a remarquée. Les **départs** et les
 * **changements de grade** gardent la date du relevé : de ceux-là, l'API ne dit
 * rien du tout.
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
            reprendre(guildId)
            val maintenant = System.currentTimeMillis() / 1000
            val apres = membres.associate { it.name to it.grade }
            val entrees = membres.associate { it.name to dateEntree(it.joined, maintenant) }
            redater(guildId, entrees)
            val avant = readSnapshot(guildId)
            val precedent = readReleve(guildId)
            val changements = if (avant == null) emptyList()
                              else diffMembres(avant, apres, maintenant, entrees, precedent)
            if (changements.isNotEmpty()) append(guildId, changements)
            writeSnapshot(guildId, apres)
            writeReleve(guildId, maintenant)
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

    /**
     * Verse au journal les mouvements observés avant qu'il n'existe.
     *
     * V-RyLune et ZyRoom-GTK tiennent chacun leur journal, et chacun ne connaît
     * que ce qu'il a vu lui-même : l'API ne rend qu'un état. Ce que le portage
     * GTK a constaté avant que celui-ci ne tienne un registre serait donc perdu
     * pour toujours — non parce que ce n'est pas arrivé, mais parce que
     * personne ne le lui a dit.
     *
     * La reprise ne se fait qu'**une fois**, marquée par un fichier témoin :
     * sans lui, une ligne effacée par l'élagage ou par l'utilisateur
     * reviendrait à chaque relevé.
     */
    private fun reprendre(id: String) {
        val temoin = File(dir, "roster-$id.reprise")
        if (temoin.isFile) return
        runCatching {
            dir.mkdirs()
            val depuis = System.currentTimeMillis() / 1000 - RETENTION_JOURS * 86400
            val connus = lignes(id).mapNotNull {
                runCatching { JSONObject(it) }.getOrNull()
            }.map { "${it.optLong("at")}|${it.optString("member")}|${it.optString("kind")}" }
                .toSet()
            val neufs = REPRISE[id].orEmpty()
                .filter { it.at >= depuis && "${it.at}|${it.member}|${it.kind}" !in connus }
            if (neufs.isNotEmpty()) append(id, neufs)
            temoin.writeText("")
        }
    }

    /**
     * Rend aux arrivées déjà journalisées leur vraie date, une fois pour toutes.
     *
     * Les lignes écrites avant que l'on sache lire `joined` portent la date du
     * relevé qui les a vues — parfois deux jours après le fait, si
     * l'application est restée fermée. L'API sait encore dater ceux qui sont
     * là ; ceux qui sont repartis entre-temps n'ont plus de date à donner et
     * gardent la leur.
     *
     * Une seule fois, marquée par un témoin : sans lui, chaque relevé relirait
     * et réécrirait le journal pour rien. Et comme l'élagage, cette passe
     * **recopie telle quelle toute ligne qu'elle n'a pas comprise** : un
     * journal ne se remplace pas par ce qu'on a su en relire.
     */
    private fun redater(id: String, entrees: Map<String, Long>) {
        if (entrees.values.none { it > 0 }) return    // flux sans le champ
        val temoin = File(dir, "roster-$id.dates")
        if (temoin.isFile) return
        val toutes = lignes(id)
        if (toutes.isEmpty()) return                  // pas encore de journal
        var corrigees = 0
        val neuves = toutes.map { ligne ->
            val o = runCatching { JSONObject(ligne) }.getOrNull()
                ?: return@map ligne                   // illisible : intacte
            // Le constat borne la correction par le haut : on ne peut pas avoir
            // vu arriver quelqu'un avant qu'il n'arrive. Si la date décodée le
            // dépasse, c'est elle qui a tort.
            val brute = if (o.optString("kind") == "arrivee")
                entrees[o.optString("member")] ?: 0L else 0L
            val quand = if (brute > 0L) minOf(brute, o.optLong("at")) else 0L
            if (quand <= 0L || o.optLong("at") == quand) ligne
            else { corrigees++; o.put("at", quand).toString() }
        }
        runCatching {
            dir.mkdirs()
            if (corrigees > 0) {
                logFile(id).writeText(neuves.joinToString("\n", postfix = "\n"))
            }
            temoin.writeText("")
        }
    }

    /**
     * La date du relevé précédent, ou 0 si on ne l'a jamais notée.
     *
     * Un fichier à part plutôt qu'une clé dans l'état : l'état est une liste de
     * noms, et y glisser autre chose ferait passer cette clé pour un membre —
     * le jour où l'on reviendrait à une version qui l'ignore, elle entrerait
     * puis sortirait de la guilde toute seule.
     */
    private fun readReleve(id: String): Long =
        runCatching { File(dir, "roster-$id.releve").readText().trim().toLong() }
            .getOrDefault(0L)

    private fun writeReleve(id: String, quand: Long) {
        runCatching {
            dir.mkdirs()
            File(dir, "roster-$id.releve").writeText(quand.toString())
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

        /**
         * Les mouvements repris d'un autre journal, par guilde.
         *
         * Ceux-ci ont été **relevés par ZyRoom-GTK le 10 août 2026 à 15 h 48**,
         * à un moment où V-RyLune ne tenait pas encore de registre pour cette
         * guilde. Ils sont datés de leur constat, non d'aujourd'hui : c'est ce
         * qui les fera sortir du journal en même temps que les autres, au bout
         * d'un mois. Rien ne les remplacera après cela, et c'est bien ainsi —
         * une reprise sert à recoller deux journaux, pas à écrire l'histoire.
         */
        private val REPRISE: Map<String, List<MouvementMembre>> = mapOf(
            // La Lune Eternelle
            "105906237" to listOf(
                MouvementMembre(1786369686, "Paty", "grade",
                                from = "Member", to = "Officer"),
                MouvementMembre(1786369686, "Thysela", "grade",
                                from = "Officer", to = "HighOfficer"),
            ),
        )
    }
}
