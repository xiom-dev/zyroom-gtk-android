package net.ryzom.zyroom.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.ryzom.zyroom.model.Outpost
import org.json.JSONObject
import java.io.File

/**
 * Le journal des prises et des pertes d'avant-postes, sur tout Atys.
 *
 * Même principe que le journal des mouvements, et pour la même raison : l'API
 * ne rend qu'un état, jamais une histoire. Deux relevés successifs comparés
 * donnent les changements ; ce qui se passe entre les deux — un avant-poste
 * pris puis repris le lendemain — se voit comme un seul changement, et deux
 * mouvements qui s'annulent ne se voient pas du tout.
 *
 * Une seule paire de fichiers pour tout le serveur, et non une par entité : la
 * carte des avant-postes ne dépend d'aucune clé d'API. Elle vit dans les
 * fichiers privés et non dans le cache — c'est justement ce que rien ne saura
 * reconstruire.
 */
class OutpostStore(private val dir: File) {

    /**
     * Un changement de main. `from` et `to` sont vides quand l'avant-poste
     * n'appartenait, ou n'appartient plus, à personne.
     */
    data class Change(
        /** Secondes Unix, comme les autres journaux. */
        val at: Long,
        val outpost: String,
        val from: String,
        val to: String,
    ) {
        val taken: Boolean get() = from.isEmpty()
        val lost: Boolean get() = to.isEmpty()
    }

    /**
     * Confronte la carte au dernier état connu, journalise ce qui a changé de
     * main, et retient le nouvel état.
     *
     * Au tout premier relevé il n'y a rien à comparer : on enregistre sans rien
     * journaliser, sinon les vingt-neuf avant-postes passeraient pour autant de
     * prises le jour de l'installation.
     */
    suspend fun record(carte: List<Outpost>): List<Change> = withContext(Dispatchers.IO) {
        val apres = carte.associate { it.code to it.guild }
        val avant = readSnapshot()
        val changements = if (avant == null) emptyList() else diff(avant, apres)
        if (changements.isNotEmpty()) append(changements)
        writeSnapshot(apres)
        changements
    }

    /** Le journal, du plus récent au plus ancien. */
    suspend fun history(): List<Change> = withContext(Dispatchers.IO) {
        val file = logFile()
        if (!file.isFile) return@withContext emptyList()
        runCatching { file.readLines() }.getOrDefault(emptyList())
            .mapNotNull { ligne ->
                if (ligne.isBlank()) null
                else runCatching {
                    val o = JSONObject(ligne)
                    Change(
                        at = o.optLong("at"),
                        outpost = o.optString("outpost"),
                        from = o.optString("from"),
                        to = o.optString("to"),
                    )
                }.getOrNull()
            }
            // Tri stable sur le seul horodatage, comme le journal des
            // mouvements : lire le fichier à l'envers retournerait aussi
            // l'ordre interne d'un même relevé.
            .sortedByDescending { it.at }
    }

    suspend fun clear() = withContext(Dispatchers.IO) {
        logFile().delete()
        Unit
    }

    /** Vrai tant qu'aucun relevé n'a été fait : le journal ne peut rien dire. */
    suspend fun jamaisReleve(): Boolean = withContext(Dispatchers.IO) {
        !snapFile().isFile
    }

    // --------------------------------------------- Ce qu'on n'a pas encore lu

    /**
     * Combien de prises **nous** concernant depuis le dernier coup d'œil.
     *
     * **Les nôtres seulement.** Le journal recense tout Atys : vingt-neuf
     * avant-postes qui changent de main au gré des guerres de guildes, et un
     * compteur qui les compterait tous serait un nombre de plus dans la barre,
     * jamais à zéro et jamais regardé. Ce qu'on veut savoir, c'est ce qui nous
     * a échappé — ou ce qu'on vient de prendre.
     *
     * Rend zéro tant qu'on ne sait pas de quelle guilde on parle.
     */
    suspend fun nonLus(guilde: String): Int = withContext(Dispatchers.IO) {
        if (guilde.isEmpty()) return@withContext 0
        val depuis = lireMarque()
        history().count { it.at > depuis && (it.from == guilde || it.to == guilde) }
    }

    /**
     * Les avant-postes qui ont changé de main et qu'on n'a pas encore vus.
     *
     * Rend `code -> Change`, le changement le plus récent pour chacun : c'est
     * ce qui permet à la carte de marquer ses lignes sans relire le journal.
     *
     * **Tout Atys, et non les nôtres seulement** — à la différence de
     * [nonLus]. Les deux ne répondent pas à la même question : le compteur est
     * un rappel sur la puce du journal, et ne doit sonner que pour ce qui nous
     * concerne ; la pastille, elle, est posée sur la carte de conquête, où
     * l'intérêt est justement de voir où ça a bougé.
     *
     * Le journal arrive du plus récent au plus ancien : le premier vu pour un
     * code est donc le bon, et les suivants sont son passé.
     */
    suspend fun recents(jours: Int = JOURS_RECENTS): Map<String, Change> =
        withContext(Dispatchers.IO) {
            val plancher = System.currentTimeMillis() / 1000 - jours * 86_400L
            val depuis = maxOf(lireMarque(), plancher)
            val vus = LinkedHashMap<String, Change>()
            history().forEach { c ->
                if (c.at > depuis && c.outpost !in vus) vus[c.outpost] = c
            }
            vus
        }

    /** Le journal vient d'être ouvert : ce qui y est devient vu. */
    suspend fun marquerLu() = withContext(Dispatchers.IO) {
        runCatching {
            dir.mkdirs()
            marqueFile().writeText(
                JSONObject().put("vu", System.currentTimeMillis() / 1000).toString())
        }
        Unit
    }

    // ------------------------------------------------------------- interne

    private fun logFile() = File(dir, "outposts.jsonl")

    private fun marqueFile() = File(dir, "outposts-vu.json")

    private fun lireMarque(): Long =
        runCatching { JSONObject(marqueFile().readText()).optLong("vu") }
            .getOrDefault(0L)

    private fun snapFile() = File(dir, "outposts-etat.json")

    internal fun diff(avant: Map<String, String>, apres: Map<String, String>): List<Change> {
        val maintenant = System.currentTimeMillis() / 1000
        // Les deux états réunis : un avant-poste rendu à personne disparaît du
        // nouvel état, et son abandon serait sinon invisible.
        return (avant.keys + apres.keys).sorted().mapNotNull { code ->
            val depuis = avant[code].orEmpty()
            val vers = apres[code].orEmpty()
            if (depuis == vers) null
            else Change(maintenant, code, depuis, vers)
        }
    }

    private fun readSnapshot(): Map<String, String>? {
        val file = snapFile()
        if (!file.isFile) return null
        return runCatching {
            val o = JSONObject(file.readText())
            o.keys().asSequence().associateWith { o.getString(it) }
        }.getOrNull()
    }

    private fun writeSnapshot(carte: Map<String, String>) {
        runCatching {
            dir.mkdirs()
            snapFile().writeText(JSONObject(carte as Map<*, *>).toString())
        }
    }

    companion object {
        /**
         * Au-delà de cet âge, une prise n'est plus une nouvelle.
         *
         * **Un plafond, en plus du marqueur de lecture.** Sans lui, une carte
         * ouverte pour la première fois après une longue absence se couvrirait
         * de pastilles — le marqueur vaut zéro tant qu'on n'a jamais ouvert le
         * journal, et tout l'historique passerait pour du neuf. Sept jours :
         * une guerre d'avant-postes se joue sur une semaine, au-delà c'est de
         * l'histoire et cela se lit dans le journal.
         */
        const val JOURS_RECENTS = 7
    }

    private fun append(changements: List<Change>) {
        runCatching {
            dir.mkdirs()
            logFile().appendText(
                changements.joinToString("") { c ->
                    JSONObject()
                        .put("at", c.at)
                        .put("outpost", c.outpost)
                        .put("from", c.from)
                        .put("to", c.to)
                        .toString() + "\n"
                }
            )
        }
    }
}
